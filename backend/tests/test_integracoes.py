"""ZapSign, Asaas e OpenRouter (IA): servicos, rotas e webhooks com HTTP SIMULADO.

Nenhum teste toca a internet: o `httpx.Client` e trocado por um MockTransport.
Foco em seguranca: so admin opera, webhook so com segredo, evento repetido nao
age duas vezes, estado e confirmado na API, segredo nunca vaza.
"""

import base64
import json
from datetime import date, timedelta

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import select

from app.api.routes.assinaturas import get_assinatura_service
from app.api.routes.financeiro import get_financeiro_service
from app.config import get_settings
from app.ia.provedores import (
    PedidoProvedor,
    ProvedorOpenRouter,
    ProvedorIndisponivelError,
    ProvedorNaoConfigurado,
    obter_provedor,
)
from app.models.assinatura import Assinatura
from app.models.cobranca import Cobranca
from app.repositories.assinatura_repository import AssinaturaRepository
from app.repositories.caso_repository import CasoRepository
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.cobranca_repository import CobrancaRepository
from app.repositories.evento_webhook_repository import EventoWebhookRepository
from app.services.assinatura_service import AssinaturaService
from app.services.asaas import AsaasService
from app.services.financeiro_service import FinanceiroService
from app.services.zapsign import ZapSignService
from tests.conftest import PADRAO

CSRF = "X-CSRF-Token"
PDF = base64.b64encode(b"%PDF-1.4\n" + b"conteudo do documento " * 20).decode()


def _cliente_http(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


# ------------------------------------------------------------------ fixtures

@pytest.fixture()
def cfg(monkeypatch):
    """Config de teste: segredos definidos e sem confirmacao na API (cada teste liga se quiser)."""
    s = get_settings()
    monkeypatch.setattr(s, "zapsign_webhook_secret", SecretStr("segredo-zap"))
    monkeypatch.setattr(s, "asaas_webhook_token", SecretStr("token-asaas"))
    monkeypatch.setattr(s, "webhooks_verificar_na_api", False)
    return s


@pytest.fixture()
def instalar_zapsign(app, db_session):
    def _instalar(handler, token: str | None = "tok-zap"):
        zap = ZapSignService(token, "https://zap.test/api/v1", _cliente_http(handler))
        app.dependency_overrides[get_assinatura_service] = lambda: AssinaturaService(
            AssinaturaRepository(db_session), ClienteRepository(db_session),
            CasoRepository(db_session), EventoWebhookRepository(db_session), zap,
        )
    return _instalar


@pytest.fixture()
def instalar_asaas(app, db_session):
    def _instalar(handler, chave: str | None = "chave-asaas"):
        asaas = AsaasService(chave, "https://asaas.test/v3", _cliente_http(handler))
        app.dependency_overrides[get_financeiro_service] = lambda: FinanceiroService(
            CobrancaRepository(db_session), ClienteRepository(db_session),
            CasoRepository(db_session), EventoWebhookRepository(db_session), asaas,
        )
    return _instalar


def _zap_ok(chamadas=None):
    def handler(req: httpx.Request) -> httpx.Response:
        if chamadas is not None:
            chamadas.append(req)
        if req.method == "POST":
            return httpx.Response(200, json={"token": "doc-123", "signers": [{"token": "sig-1", "sign_url": "https://app.zapsign.com.br/verificar/sig-1"}]})
        return httpx.Response(200, json={"token": "doc-123", "status": "signed"})
    return handler


@pytest.fixture()
def cliente_completo(criar_cliente):
    return criar_cliente(nome="Maria da Silva", cpf_cnpj="12345678909", email="maria@exemplo.com", telefone="75999991234")


# ============================================================ ZapSign: envio

class TestEnvioZapSign:
    def _enviar(self, client, csrf, cliente_id, pdf=PDF, **extra):
        return client.post("/api/assinaturas", headers={CSRF: csrf}, json={"titulo": "Procuração", "cliente_id": cliente_id, "pdf_base64": pdf, **extra})

    def test_envia_e_guarda_sem_expor_tokens(self, client, csrf_admin, cliente_completo, instalar_zapsign, db_session):
        chamadas: list = []
        instalar_zapsign(_zap_ok(chamadas))
        resp = self._enviar(client, csrf_admin, cliente_completo.id)
        assert resp.status_code == 201, resp.text
        corpo = resp.json()
        assert corpo["status"] == "ENVIADO" and corpo["link_assinatura"].startswith("https://app.zapsign")
        assert "token" not in json.dumps(corpo).lower() and "doc-123" not in json.dumps(corpo)
        req = chamadas[0]
        assert req.headers["authorization"] == "Bearer tok-zap"
        enviado = json.loads(req.content)
        sig = enviado["signers"][0]
        assert enviado["base64_pdf"] == PDF and sig["name"] == "Maria da Silva" and sig["phone_number"] == "75999991234" and sig["phone_country"] == "55"
        salvo = db_session.scalars(select(Assinatura)).one()
        assert salvo.zapsign_doc_token == "doc-123" and len(salvo.pdf_sha256) == 64

    def test_so_admin_envia(self, client, csrf_de, cliente_completo, instalar_zapsign):
        instalar_zapsign(_zap_ok())
        resp = self._enviar(client, csrf_de(PADRAO), cliente_completo.id)
        assert resp.status_code == 403

    def test_exige_login(self, client, cliente_completo):
        assert client.post("/api/assinaturas", json={}).status_code == 401

    @pytest.mark.parametrize("pdf", [base64.b64encode(b"nao e um pdf " * 20).decode(), "%%%%" * 40])
    def test_recusa_arquivo_que_nao_e_pdf(self, client, csrf_admin, cliente_completo, instalar_zapsign, pdf):
        instalar_zapsign(_zap_ok())
        assert self._enviar(client, csrf_admin, cliente_completo.id, pdf=pdf).status_code == 422

    def test_cliente_sem_contato_422(self, client, csrf_admin, criar_cliente, instalar_zapsign):
        instalar_zapsign(_zap_ok())
        c = criar_cliente(nome="Sem Contato")
        assert self._enviar(client, csrf_admin, c.id).status_code == 422

    def test_cliente_inexistente_404(self, client, csrf_admin, instalar_zapsign):
        instalar_zapsign(_zap_ok())
        assert self._enviar(client, csrf_admin, 9999).status_code == 404

    def test_caso_inexistente_404(self, client, csrf_admin, cliente_completo, instalar_zapsign):
        instalar_zapsign(_zap_ok())
        assert self._enviar(client, csrf_admin, cliente_completo.id, caso_id=9999).status_code == 404

    def test_campo_extra_e_422(self, client, csrf_admin, cliente_completo, instalar_zapsign):
        instalar_zapsign(_zap_ok())
        assert self._enviar(client, csrf_admin, cliente_completo.id, status="ASSINADO").status_code == 422

    def test_provedor_recusa_credencial_vira_502_sem_vazar_token(self, client, csrf_admin, cliente_completo, instalar_zapsign):
        instalar_zapsign(lambda req: httpx.Response(401, json={"detail": "bad token tok-zap"}))
        resp = self._enviar(client, csrf_admin, cliente_completo.id)
        assert resp.status_code == 502 and "tok-zap" not in resp.text

    def test_sem_token_configurado_e_503(self, client, csrf_admin, cliente_completo, instalar_zapsign):
        instalar_zapsign(_zap_ok(), token=None)
        assert self._enviar(client, csrf_admin, cliente_completo.id).status_code == 503

    def test_timeout_vira_502(self, client, csrf_admin, cliente_completo, instalar_zapsign):
        def lento(req):
            raise httpx.ReadTimeout("lento", request=req)
        instalar_zapsign(lento)
        assert self._enviar(client, csrf_admin, cliente_completo.id).status_code == 502


# ========================================================= ZapSign: webhook

def _assinatura(db_session, cliente, token="doc-123", status="ENVIADO"):
    a = Assinatura(cliente_id=cliente.id, titulo="Procuração", zapsign_doc_token=token, status=status, signatario_nome=cliente.nome, pdf_sha256="0" * 64)
    db_session.add(a)
    db_session.commit()
    return a


class TestWebhookZapSign:
    URL = "/api/v1/webhooks/zapsign"
    EVENTO = {"event_type": "doc_signed", "token": "doc-123", "status": "signed"}

    def test_sem_segredo_configurado_fecha(self, client, monkeypatch, instalar_zapsign):
        monkeypatch.setattr(get_settings(), "zapsign_webhook_secret", None)
        instalar_zapsign(_zap_ok())
        assert client.post(self.URL, json=self.EVENTO).status_code == 503

    @pytest.mark.parametrize("cabecalho", [{}, {"X-Zapsign-Secret": "errado"}])
    def test_segredo_ausente_ou_errado_401(self, client, cfg, instalar_zapsign, cabecalho):
        instalar_zapsign(_zap_ok())
        assert client.post(self.URL, json=self.EVENTO, headers=cabecalho).status_code == 401

    def test_assinado_atualiza_status_sem_sessao_nem_csrf(self, client, cfg, instalar_zapsign, cliente_completo, db_session):
        instalar_zapsign(_zap_ok())
        a = _assinatura(db_session, cliente_completo)
        resp = client.post(self.URL, json=self.EVENTO, headers={"X-Zapsign-Secret": "segredo-zap"})
        assert resp.status_code == 200 and resp.json()["status"] == "status=ASSINADO"
        db_session.refresh(a)
        assert a.status == "ASSINADO" and a.assinado_em is not None

    def test_evento_repetido_nao_age_duas_vezes(self, client, cfg, instalar_zapsign, cliente_completo, db_session):
        instalar_zapsign(_zap_ok())
        _assinatura(db_session, cliente_completo)
        h = {"X-Zapsign-Secret": "segredo-zap"}
        assert client.post(self.URL, json=self.EVENTO, headers=h).json()["status"] == "status=ASSINADO"
        assert client.post(self.URL, json=self.EVENTO, headers=h).json()["status"] == "duplicado"

    def test_documento_desconhecido_e_ignorado_com_200(self, client, cfg, instalar_zapsign):
        instalar_zapsign(_zap_ok())
        resp = client.post(self.URL, json={**self.EVENTO, "token": "nao-existe"}, headers={"X-Zapsign-Secret": "segredo-zap"})
        assert resp.status_code == 200 and "ignorado" in resp.json()["status"]

    def test_confirma_na_api_e_nao_confia_no_aviso(self, client, cfg, monkeypatch, instalar_zapsign, cliente_completo, db_session):
        monkeypatch.setattr(cfg, "webhooks_verificar_na_api", True)
        instalar_zapsign(lambda req: httpx.Response(200, json={"token": "doc-123", "status": "pending"}))
        a = _assinatura(db_session, cliente_completo)
        resp = client.post(self.URL, json=self.EVENTO, headers={"X-Zapsign-Secret": "segredo-zap"})
        assert resp.status_code == 200 and "ignorado" in resp.json()["status"]
        db_session.refresh(a)
        assert a.status == "ENVIADO"

    def test_falha_ao_confirmar_pede_reenvio(self, client, cfg, monkeypatch, instalar_zapsign, cliente_completo, db_session):
        monkeypatch.setattr(cfg, "webhooks_verificar_na_api", True)
        instalar_zapsign(lambda req: httpx.Response(500))
        _assinatura(db_session, cliente_completo)
        assert client.post(self.URL, json=self.EVENTO, headers={"X-Zapsign-Secret": "segredo-zap"}).status_code == 503

    def test_json_invalido_400(self, client, cfg, instalar_zapsign):
        instalar_zapsign(_zap_ok())
        resp = client.post(self.URL, content=b"{nao json", headers={"X-Zapsign-Secret": "segredo-zap", "Content-Type": "application/json"})
        assert resp.status_code == 400

    def test_assinado_nunca_volta_atras(self, client, cfg, instalar_zapsign, cliente_completo, db_session):
        instalar_zapsign(_zap_ok())
        a = _assinatura(db_session, cliente_completo, status="ASSINADO")
        resp = client.post(self.URL, json={**self.EVENTO, "event_type": "doc_refused", "status": "refused"}, headers={"X-Zapsign-Secret": "segredo-zap"})
        assert resp.status_code == 200
        db_session.refresh(a)
        assert a.status == "ASSINADO"


# ============================================================ Asaas: cobrança

def _asaas_handler(chamadas: list, *, parcelas: int = 1):
    hoje = (date.today() + timedelta(days=10)).isoformat()

    def handler(req: httpx.Request) -> httpx.Response:
        chamadas.append((req.method, req.url.path))
        assert req.headers["access_token"] == "chave-asaas"
        if req.method == "GET" and req.url.path.endswith("/customers"):
            return httpx.Response(200, json={"data": []})
        if req.method == "POST" and req.url.path.endswith("/customers"):
            return httpx.Response(200, json={"id": "cus_1"})
        if req.method == "POST" and req.url.path.endswith("/payments"):
            corpo = json.loads(req.content)
            assert corpo["customer"] == "cus_1" and corpo["billingType"] in ("PIX", "BOLETO")
            base = {"id": "pay_1", "status": "PENDING", "dueDate": hoje, "invoiceUrl": "https://asaas.test/i/pay_1"}
            if parcelas > 1:
                return httpx.Response(200, json={**base, "installment": "ins_1", "value": corpo["totalValue"] / parcelas})
            return httpx.Response(200, json={**base, "value": corpo["value"]})
        if req.method == "GET" and "/installments/" in req.url.path:
            itens = [{"id": f"pay_{i}", "status": "PENDING", "value": 500.0, "dueDate": hoje, "installment": "ins_1", "invoiceUrl": f"https://asaas.test/i/{i}"} for i in range(1, parcelas + 1)]
            return httpx.Response(200, json={"data": itens})
        return httpx.Response(404)

    return handler


class TestEmissaoAsaas:
    def _emitir(self, client, csrf, cliente_id, **extra):
        corpo = {"cliente_id": cliente_id, "valor": "1500.00", "vencimento": (date.today() + timedelta(days=10)).isoformat(), "forma": "PIX", "descricao": "Honorários", **extra}
        return client.post("/api/financeiro/cobrancas", headers={CSRF: csrf}, json=corpo)

    def test_emite_pix_cria_cliente_no_asaas_uma_vez(self, client, csrf_admin, cliente_completo, instalar_asaas, db_session):
        chamadas: list = []
        instalar_asaas(_asaas_handler(chamadas))
        r1 = self._emitir(client, csrf_admin, cliente_completo.id)
        assert r1.status_code == 201, r1.text
        assert r1.json()[0]["status"] == "PENDENTE" and r1.json()[0]["link_fatura"].startswith("https://asaas.test")
        db_session.refresh(cliente_completo)
        assert cliente_completo.asaas_customer_id == "cus_1"
        # segunda cobranca: nao cadastra o cliente de novo
        db_session.query(Cobranca).delete()
        db_session.commit()
        self._emitir(client, csrf_admin, cliente_completo.id)
        assert [c for c in chamadas if c == ("POST", "/v3/customers")] == [("POST", "/v3/customers")]

    def test_parcelada_guarda_uma_linha_por_parcela(self, client, csrf_admin, cliente_completo, instalar_asaas, db_session):
        instalar_asaas(_asaas_handler([], parcelas=3))
        resp = self._emitir(client, csrf_admin, cliente_completo.id, valor="1500.00", parcelas=3, forma="BOLETO")
        assert resp.status_code == 201, resp.text
        linhas = resp.json()
        assert [c["parcela"] for c in linhas] == [1, 2, 3] and all(c["total_parcelas"] == 3 for c in linhas)
        assert db_session.query(Cobranca).count() == 3

    def test_so_admin_emite(self, client, csrf_de, cliente_completo, instalar_asaas):
        instalar_asaas(_asaas_handler([]))
        assert self._emitir(client, csrf_de(PADRAO), cliente_completo.id).status_code == 403

    @pytest.mark.parametrize("extra", [
        {"valor": "0"}, {"valor": "-10"}, {"valor": "2000000.00"}, {"forma": "CARTAO"},
        {"parcelas": 0}, {"parcelas": 25}, {"vencimento": "2020-01-01"}, {"status": "RECEBIDA"},
    ])
    def test_entradas_invalidas_422(self, client, csrf_admin, cliente_completo, instalar_asaas, extra):
        instalar_asaas(_asaas_handler([]))
        assert self._emitir(client, csrf_admin, cliente_completo.id, **extra).status_code == 422

    def test_cliente_sem_cpf_422(self, client, csrf_admin, criar_cliente, instalar_asaas):
        instalar_asaas(_asaas_handler([]))
        c = criar_cliente(nome="Sem Documento")
        assert self._emitir(client, csrf_admin, c.id).status_code == 422

    def test_cliente_inexistente_404(self, client, csrf_admin, instalar_asaas):
        instalar_asaas(_asaas_handler([]))
        assert self._emitir(client, csrf_admin, 9999).status_code == 404

    def test_asaas_recusa_credencial_502_sem_vazar_chave(self, client, csrf_admin, cliente_completo, instalar_asaas):
        instalar_asaas(lambda req: httpx.Response(401, json={"errors": [{"description": "chave-asaas invalida"}]}))
        resp = self._emitir(client, csrf_admin, cliente_completo.id)
        assert resp.status_code == 502 and "chave-asaas" not in resp.text

    def test_sem_chave_configurada_503(self, client, csrf_admin, cliente_completo, instalar_asaas):
        instalar_asaas(_asaas_handler([]), chave=None)
        assert self._emitir(client, csrf_admin, cliente_completo.id).status_code == 503

    def test_resumo_financeiro(self, client, csrf_admin, cliente_completo, instalar_asaas, db_session):
        instalar_asaas(_asaas_handler([]))
        self._emitir(client, csrf_admin, cliente_completo.id)
        r = client.get(f"/api/financeiro/clientes/{cliente_completo.id}/resumo").json()
        assert r["pendente"] == "1500.00" and r["recebido"] == "0.00" and r["em_dia"] is True


# ========================================================== Asaas: webhook

def _cobranca(db_session, cliente, payment_id="pay_1", status="PENDENTE"):
    c = Cobranca(cliente_id=cliente.id, asaas_payment_id=payment_id, forma="PIX", valor=1500, vencimento=date.today() + timedelta(days=5), status=status)
    db_session.add(c)
    db_session.commit()
    return c


def _evento_asaas(evento="PAYMENT_RECEIVED", id_evento="evt_1", payment="pay_1"):
    return {"id": id_evento, "event": evento, "payment": {"id": payment, "status": "RECEIVED"}}


class TestWebhookAsaas:
    URL = "/api/v1/webhooks/asaas"
    H = {"asaas-access-token": "token-asaas"}

    def test_sem_token_configurado_fecha(self, client, monkeypatch, instalar_asaas):
        monkeypatch.setattr(get_settings(), "asaas_webhook_token", None)
        instalar_asaas(_asaas_handler([]))
        assert client.post(self.URL, json=_evento_asaas()).status_code == 503

    @pytest.mark.parametrize("h", [{}, {"asaas-access-token": "errado"}])
    def test_token_ausente_ou_errado_401(self, client, cfg, instalar_asaas, h):
        instalar_asaas(_asaas_handler([]))
        assert client.post(self.URL, json=_evento_asaas(), headers=h).status_code == 401

    def test_recebido_marca_paga(self, client, cfg, instalar_asaas, cliente_completo, db_session):
        instalar_asaas(_asaas_handler([]))
        c = _cobranca(db_session, cliente_completo)
        resp = client.post(self.URL, json=_evento_asaas(), headers=self.H)
        assert resp.status_code == 200 and resp.json()["status"] == "status=RECEBIDA"
        db_session.refresh(c)
        assert c.status == "RECEBIDA" and c.pago_em is not None

    def test_vencido_marca_vencida(self, client, cfg, instalar_asaas, cliente_completo, db_session):
        instalar_asaas(_asaas_handler([]))
        c = _cobranca(db_session, cliente_completo)
        client.post(self.URL, json=_evento_asaas("PAYMENT_OVERDUE", "evt_2"), headers=self.H)
        db_session.refresh(c)
        assert c.status == "VENCIDA"

    def test_evento_repetido_e_duplicado(self, client, cfg, instalar_asaas, cliente_completo, db_session):
        instalar_asaas(_asaas_handler([]))
        _cobranca(db_session, cliente_completo)
        assert client.post(self.URL, json=_evento_asaas(), headers=self.H).json()["status"] == "status=RECEBIDA"
        assert client.post(self.URL, json=_evento_asaas(), headers=self.H).json()["status"] == "duplicado"

    def test_evento_atrasado_nao_desfaz_pagamento(self, client, cfg, instalar_asaas, cliente_completo, db_session):
        instalar_asaas(_asaas_handler([]))
        c = _cobranca(db_session, cliente_completo, status="RECEBIDA")
        resp = client.post(self.URL, json=_evento_asaas("PAYMENT_OVERDUE", "evt_9"), headers=self.H)
        assert resp.status_code == 200
        db_session.refresh(c)
        assert c.status == "RECEBIDA"

    def test_cobranca_desconhecida_e_evento_nao_tratado_ignorados(self, client, cfg, instalar_asaas):
        instalar_asaas(_asaas_handler([]))
        assert "ignorado" in client.post(self.URL, json=_evento_asaas(payment="pay_x"), headers=self.H).json()["status"]
        assert "ignorado" in client.post(self.URL, json=_evento_asaas("PAYMENT_CREATED"), headers=self.H).json()["status"]

    def test_confirma_na_api_e_nao_confia_no_aviso(self, client, cfg, monkeypatch, instalar_asaas, cliente_completo, db_session):
        monkeypatch.setattr(cfg, "webhooks_verificar_na_api", True)
        instalar_asaas(lambda req: httpx.Response(200, json={"id": "pay_1", "status": "PENDING"}))
        c = _cobranca(db_session, cliente_completo)
        client.post(self.URL, json=_evento_asaas(), headers=self.H)
        db_session.refresh(c)
        assert c.status == "PENDENTE" and c.pago_em is None  # o Asaas disse que ainda esta pendente

    def test_falha_ao_confirmar_pede_reenvio(self, client, cfg, monkeypatch, instalar_asaas, cliente_completo, db_session):
        monkeypatch.setattr(cfg, "webhooks_verificar_na_api", True)
        instalar_asaas(lambda req: httpx.Response(500))
        _cobranca(db_session, cliente_completo)
        assert client.post(self.URL, json=_evento_asaas(), headers=self.H).status_code == 503


# ============================================================ IA: OpenRouter

def _openrouter(handler) -> ProvedorOpenRouter:
    return ProvedorOpenRouter(
        "sk-or-teste", "google/gemma-4-31b-it:free", site_url="http://localhost:5173",
        app_nome="Jadilson Silva Adv.", http=_cliente_http(handler),
    )


def _resposta_ia(texto: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": texto}}]})


PEDIDO = PedidoProvedor(tarefa="revisar", sistema="SISTEMA", usuario="USUARIO", area=None)


class TestProvedorOpenRouter:
    def test_chamada_correta_e_texto_devolvido(self):
        vistos: list = []

        def handler(req):
            vistos.append(req)
            return _resposta_ia('{"perguntas": [], "sugestoes": []}')

        texto = _openrouter(handler).gerar(PEDIDO)
        req = vistos[0]
        corpo = json.loads(req.content)
        assert str(req.url) == "https://openrouter.ai/api/v1/chat/completions"
        assert req.headers["authorization"] == "Bearer sk-or-teste" and req.headers["http-referer"] == "http://localhost:5173"
        assert corpo["model"] == "google/gemma-4-31b-it:free"
        assert corpo["messages"] == [{"role": "system", "content": "SISTEMA"}, {"role": "user", "content": "USUARIO"}]
        assert json.loads(texto) == {"perguntas": [], "sugestoes": []}

    @pytest.mark.parametrize("status", [401, 402, 403, 404, 429, 500, 502])
    def test_erros_viram_indisponivel_sem_vazar_chave(self, status):
        p = _openrouter(lambda req: httpx.Response(status, json={"error": {"message": "sk-or-teste invalida"}}))
        with pytest.raises(ProvedorIndisponivelError) as exc:
            p.gerar(PEDIDO)
        assert "sk-or-teste" not in str(exc.value)

    def test_http_200_com_erro_no_corpo(self):
        p = _openrouter(lambda req: httpx.Response(200, json={"error": {"message": "provider saturado", "code": 503}}))
        with pytest.raises(ProvedorIndisponivelError):
            p.gerar(PEDIDO)

    def test_timeout_resposta_vazia_e_formato_inesperado(self):
        def lento(req):
            raise httpx.ReadTimeout("x", request=req)

        with pytest.raises(ProvedorIndisponivelError):
            _openrouter(lento).gerar(PEDIDO)
        for corpo in ({"choices": []}, {"choices": [{"message": {"content": None}}]}, {"choices": [{"message": {"content": "  "}}]}, {"oi": 1}):
            with pytest.raises(ProvedorIndisponivelError):
                _openrouter(lambda req, c=corpo: httpx.Response(200, json=c)).gerar(PEDIDO)

    def test_completar_usa_poucos_tokens(self):
        vistos: list = []
        p = _openrouter(lambda req: (vistos.append(req), _resposta_ia(" continua"))[1])
        p.gerar(PedidoProvedor(tarefa="completar", sistema="S", usuario="U"))
        assert json.loads(vistos[0].content)["max_tokens"] == 300

    def test_obter_provedor_sem_chave_e_nao_configurado(self, monkeypatch):
        monkeypatch.setattr(get_settings(), "openrouter_api_key", None)
        assert isinstance(obter_provedor("openrouter"), ProvedorNaoConfigurado)

    def test_obter_provedor_com_chave_usa_modelo_google_gratuito(self, monkeypatch):
        monkeypatch.setattr(get_settings(), "openrouter_api_key", SecretStr("sk-or-x"))
        p = obter_provedor("openrouter")
        assert isinstance(p, ProvedorOpenRouter) and p._modelo.startswith("google/") and p._modelo.endswith(":free")

    def test_pii_e_mascarada_antes_de_chegar_ao_provedor(self, app, client, csrf_de, db_session):
        """O que o modelo recebe nunca tem CPF, CNPJ, e-mail nem telefone."""
        from app.api.routes.ia import get_ia_servico
        from app.ia.servico import IAServico
        from app.repositories.uso_ia_repository import UsoIARepository

        vistos: list = []

        def handler(req):
            vistos.append(json.loads(req.content))
            return _resposta_ia("```json\n{\"perguntas\": [], \"sugestoes\": []}\n```")

        provedor = _openrouter(handler)
        app.dependency_overrides[get_ia_servico] = lambda: IAServico(provedor, UsoIARepository(db_session))

        texto = "Maria, CPF 123.456.789-09, CNPJ 12.345.678/0001-90, maria@x.com, tel (75) 99999-1234, requer a procedencia."
        resp = client.post("/api/ia/sugerir", headers={CSRF: csrf_de(PADRAO)}, json={"tarefa": "revisar", "texto_documento": texto, "pedido": "revise meu CPF 111.222.333-44"})
        assert resp.status_code == 200, resp.text
        enviado = json.dumps(vistos[0], ensure_ascii=False)
        for dado in ("123.456.789-09", "12.345.678/0001-90", "maria@x.com", "99999-1234", "111.222.333-44"):
            assert dado not in enviado
        assert "[CPF]" in enviado and "[E-MAIL]" in enviado
        assert resp.json()["simulado"] is False and resp.json()["provedor"] == "openrouter"

    def test_prompt_de_sistema_inclui_exemplos_few_shot_da_materia(self):
        from app.ia import carregador
        from app.ia.schemas import AreaIA

        carregador.limpar_cache()
        for area in (AreaIA.TRABALHISTA, AreaIA.BANCARIO, AreaIA.PREVIDENCIARIO):
            assert "few-shot" in carregador.instrucoes_sistema(area)
        assert "few-shot" not in carregador.instrucoes_sistema(AreaIA.GERAL)
