"""Pedido livre, contexto do processo e robustez do OpenRouter (modelo gratuito saturado)."""

import json

import httpx
import pytest

from app.api.routes.ia import get_ia_servico
from app.ia.provedores import PedidoProvedor, ProvedorIndisponivelError, ProvedorOpenRouter
from app.ia.servico import IAServico
from app.repositories.uso_ia_repository import UsoIARepository
from tests.conftest import PADRAO

CSRF = "X-CSRF-Token"


def _ok(texto: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": texto}}]})


def _prov(handler, **kw) -> ProvedorOpenRouter:
    return ProvedorOpenRouter("sk-or-x", "google/gemma-4-31b-it:free", espera_retry=0, http=httpx.Client(transport=httpx.MockTransport(handler)), **kw)


class TestRobustezOpenRouter:
    def test_envia_modelos_reserva(self):
        vistos: list = []
        p = _prov(lambda r: (vistos.append(json.loads(r.content)), _ok("x"))[1], alternativos=("google/gemma-4-26b-a4b-it:free",))
        p.gerar(PedidoProvedor(tarefa="revisar", sistema="S", usuario="U"))
        assert vistos[0]["models"] == ["google/gemma-4-31b-it:free", "google/gemma-4-26b-a4b-it:free"]

    def test_autocompletar_desliga_o_raciocinio_e_pedido_normal_nao(self):
        vistos: list = []
        p = _prov(lambda r: (vistos.append(json.loads(r.content)), _ok("x"))[1])
        p.gerar(PedidoProvedor(tarefa="completar", sistema="S", usuario="U"))
        p.gerar(PedidoProvedor(tarefa="livre", sistema="S", usuario="U"))
        assert vistos[0]["reasoning"] == {"enabled": False} and "reasoning" not in vistos[1]

    def test_tenta_de_novo_quando_o_modelo_gratuito_esta_saturado(self):
        chamadas = []

        def handler(req):
            chamadas.append(1)
            return httpx.Response(429, json={"error": {"message": "rate limited"}}) if len(chamadas) == 1 else _ok("resposta")

        assert _prov(handler).gerar(PedidoProvedor(tarefa="livre", sistema="S", usuario="U")) == "resposta"
        assert len(chamadas) == 2

    def test_desiste_depois_da_segunda_tentativa_com_mensagem_util(self):
        chamadas = []
        p = _prov(lambda r: (chamadas.append(1), httpx.Response(429, json={}))[1])
        with pytest.raises(ProvedorIndisponivelError) as exc:
            p.gerar(PedidoProvedor(tarefa="livre", sistema="S", usuario="U"))
        assert len(chamadas) == 2 and "Google AI Studio" in str(exc.value)

    def test_autocompletar_nao_repete_a_chamada(self):
        chamadas = []
        p = _prov(lambda r: (chamadas.append(1), httpx.Response(429, json={}))[1])
        with pytest.raises(ProvedorIndisponivelError):
            p.gerar(PedidoProvedor(tarefa="completar", sistema="S", usuario="U"))
        assert len(chamadas) == 1


class TestPedidoLivre:
    def _instalar(self, app, db_session, handler):
        provedor = _prov(handler)
        app.dependency_overrides[get_ia_servico] = lambda: IAServico(provedor, UsoIARepository(db_session))

    def test_o_pedido_do_advogado_vai_no_prompt_com_a_instrucao_de_obedecer(self, app, client, csrf_de, db_session):
        vistos: list = []
        self._instalar(app, db_session, lambda r: (vistos.append(json.loads(r.content)), _ok('{"perguntas": [], "sugestoes": [{"titulo": "Parágrafo", "html": "<p>texto</p>"}]}'))[1])
        pedido = "escreva um parágrafo curto pedindo a inversão do ônus da prova"
        resp = client.post("/api/ia/sugerir", headers={CSRF: csrf_de(PADRAO)}, json={"tarefa": "livre", "pedido": pedido, "area": "bancario"})
        assert resp.status_code == 200, resp.text
        usuario = vistos[0]["messages"][1]["content"]
        assert pedido in usuario and "Faça exatamente o que ele pediu" in usuario
        assert resp.json()["sugestoes"][0]["titulo"] == "Parágrafo"

    def test_contexto_do_processo_vai_ao_modelo_mascarado(self, app, client, csrf_de, db_session):
        vistos: list = []
        self._instalar(app, db_session, lambda r: (vistos.append(json.loads(r.content)), _ok('{"perguntas": [], "sugestoes": []}'))[1])
        ctx = "Processo: 0000001-12.2026.8.00.0100\nCliente: Maria, CPF 123.456.789-09, tel (75) 99999-1234\nFase atual: Instrução"
        client.post("/api/ia/sugerir", headers={CSRF: csrf_de(PADRAO)}, json={"tarefa": "resumo", "pedido": "resuma", "contexto_processo": ctx})
        usuario = vistos[0]["messages"][1]["content"]
        assert "DADOS DO PROCESSO" in usuario and "0000001-12.2026.8.00.0100" in usuario and "Instrução" in usuario
        assert "123.456.789-09" not in usuario and "99999-1234" not in usuario

    def test_simulado_resume_o_contexto_informado_em_vez_de_perguntar(self, client, csrf_de):
        ctx = "Processo: 0000001-12.2026.8.00.0100\nCliente: Maria da Silva\nFase atual: Instrução"
        corpo = client.post("/api/ia/sugerir", headers={CSRF: csrf_de(PADRAO)}, json={"tarefa": "resumo", "contexto_processo": ctx}).json()
        assert corpo["perguntas"] == [] and "Maria da Silva" in corpo["sugestoes"][0]["html"]

    def test_simulado_avisa_que_pedido_livre_precisa_da_ia_real(self, client, csrf_de):
        corpo = client.post("/api/ia/sugerir", headers={CSRF: csrf_de(PADRAO)}, json={"tarefa": "livre", "pedido": "faça algo"}).json()
        assert corpo["sugestoes"][0]["tipo"] == "Aviso"

    def test_provedor_saturado_vira_503_com_mensagem_do_servidor(self, app, client, csrf_de, db_session):
        self._instalar(app, db_session, lambda r: httpx.Response(429, json={}))
        resp = client.post("/api/ia/sugerir", headers={CSRF: csrf_de(PADRAO)}, json={"tarefa": "livre", "pedido": "oi"})
        assert resp.status_code == 503 and "saturado" in resp.json()["detail"]
