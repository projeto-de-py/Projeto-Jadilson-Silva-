"""Andamentos do caso: registro manual, escopo de acesso e importacao do tribunal (DataJud)."""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.api.routes.consultas import get_processo_service
from app.integrations.datajud import Movimento, ProcessoExterno
from app.integrations.erros import IntegracaoNaoConfiguradaError
from app.services.processo_externo_service import ConsultaProcesso
from tests.conftest import ADMIN, PADRAO

CSRF = "X-CSRF-Token"
NUMERO = "0000001-00.2026.8.26.0100"


def _instancia(*movimentos: Movimento) -> ProcessoExterno:
    return ProcessoExterno(
        numero=NUMERO, tribunal="TJSP", grau="G1", classe="Procedimento Comum",
        assuntos=("Contratos bancarios",), orgao_julgador="1a Vara Civel",
        data_ajuizamento=datetime(2026, 1, 10), movimentos=tuple(movimentos),
    )


class ProcessoFalso:
    """Substitui o DataJud: devolve sempre as movimentacoes combinadas no teste."""

    def __init__(self, *movimentos: Movimento, encontrado: bool = True):
        self.movimentos, self.encontrado, self.chamadas = movimentos, encontrado, 0

    def consultar(self, numero: str) -> ConsultaProcesso:
        self.chamadas += 1
        instancias = [_instancia(*self.movimentos)] if self.encontrado else []
        return ConsultaProcesso(numero=NUMERO, tribunal="tjsp", instancias=instancias)


@pytest.fixture()
def usar_datajud(app):
    def _usar(falso) -> None:
        app.dependency_overrides[get_processo_service] = lambda: falso

    return _usar


@pytest.fixture()
def caso(criar_caso):
    return criar_caso(numero_processo=NUMERO)


class TestRegistroManual:
    def test_registra_e_lista_do_mais_recente_para_o_mais_antigo(self, client, csrf_de, caso):
        h = {CSRF: csrf_de(ADMIN)}
        for titulo, dia in (("Citação", "2026-03-01"), ("Sentença", "2026-05-20"), ("Contestação", "2026-04-10")):
            r = client.post(f"/api/casos/{caso.id}/andamentos", headers=h, json={"titulo": titulo, "ocorrido_em": dia})
            assert r.status_code == 201 and r.json()["origem"] == "MANUAL"
        lista = client.get(f"/api/casos/{caso.id}/andamentos").json()
        assert [a["titulo"] for a in lista] == ["Sentença", "Contestação", "Citação"]

    def test_data_padrao_e_hoje(self, client, csrf_de, caso):
        r = client.post(f"/api/casos/{caso.id}/andamentos", headers={CSRF: csrf_de(ADMIN)}, json={"titulo": "Petição juntada"})
        assert r.status_code == 201
        assert datetime.fromisoformat(r.json()["ocorrido_em"]).date() == datetime.now(timezone.utc).date()

    @pytest.mark.parametrize(
        "corpo",
        [
            {"titulo": ""},
            {"titulo": "x"},
            {"titulo": "ok", "ocorrido_em": (date.today() + timedelta(days=2)).isoformat()},
            {"titulo": "ok", "campo_inventado": 1},
        ],
    )
    def test_entrada_invalida_vira_422(self, client, csrf_de, caso, corpo):
        r = client.post(f"/api/casos/{caso.id}/andamentos", headers={CSRF: csrf_de(ADMIN)}, json=corpo)
        assert r.status_code == 422

    def test_exige_login_e_csrf(self, client, csrf_de, caso):
        assert client.post(f"/api/casos/{caso.id}/andamentos", json={"titulo": "Sem login"}).status_code in (401, 403)
        csrf_de(ADMIN)
        assert client.post(f"/api/casos/{caso.id}/andamentos", json={"titulo": "Sem csrf"}).status_code == 403

    def test_apaga_andamento_manual(self, client, csrf_de, caso):
        h = {CSRF: csrf_de(ADMIN)}
        criado = client.post(f"/api/casos/{caso.id}/andamentos", headers=h, json={"titulo": "Errado"}).json()
        assert client.delete(f"/api/casos/{caso.id}/andamentos/{criado['id']}", headers=h).status_code == 204
        assert client.get(f"/api/casos/{caso.id}/andamentos").json() == []
        assert client.delete(f"/api/casos/{caso.id}/andamentos/{criado['id']}", headers=h).status_code == 404


class TestEscopo:
    def test_sem_acesso_ao_caso_e_404_em_tudo(self, client, csrf_de, caso, advogada):
        h = {CSRF: csrf_de(PADRAO)}
        assert client.get(f"/api/casos/{caso.id}/andamentos").status_code == 404
        assert client.post(f"/api/casos/{caso.id}/andamentos", headers=h, json={"titulo": "Invasão"}).status_code == 404
        assert client.post(f"/api/casos/{caso.id}/andamentos/sincronizar", headers=h).status_code == 404

    def test_com_acesso_ao_caso_registra_e_lista(self, client, csrf_de, caso, advogada, conceder_acesso):
        conceder_acesso(caso, advogada)
        h = {CSRF: csrf_de(PADRAO)}
        assert client.post(f"/api/casos/{caso.id}/andamentos", headers=h, json={"titulo": "Despacho"}).status_code == 201
        assert len(client.get(f"/api/casos/{caso.id}/andamentos").json()) == 1

    def test_andamento_de_outro_caso_nao_e_apagado_por_este_caminho(self, client, csrf_de, caso, criar_caso):
        h = {CSRF: csrf_de(ADMIN)}
        outro = criar_caso()
        criado = client.post(f"/api/casos/{outro.id}/andamentos", headers=h, json={"titulo": "Do outro caso"}).json()
        assert client.delete(f"/api/casos/{caso.id}/andamentos/{criado['id']}", headers=h).status_code == 404


class TestSincronizacaoComODataJud:
    def _movimentos(self):
        return (
            Movimento(datetime(2026, 5, 20, 14, 30, tzinfo=timezone.utc), "Sentença", "Julgado procedente"),
            Movimento(datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc), "Citação"),
            Movimento(None, "Sem data"),
        )

    def test_importa_as_movimentacoes_com_data(self, client, csrf_de, caso, usar_datajud):
        usar_datajud(ProcessoFalso(*self._movimentos()))
        r = client.post(f"/api/casos/{caso.id}/andamentos/sincronizar", headers={CSRF: csrf_de(ADMIN)})
        assert r.status_code == 200
        assert (r.json()["novos"], r.json()["encontrado"]) == (2, True)
        lista = client.get(f"/api/casos/{caso.id}/andamentos").json()
        assert [a["titulo"] for a in lista] == ["Sentença", "Citação"]
        assert all(a["origem"] == "DATAJUD" for a in lista)
        assert "1a Vara Civel" in lista[0]["descricao"] and "Julgado procedente" in lista[0]["descricao"]

    def test_repetir_a_sincronizacao_nao_duplica(self, client, csrf_de, caso, usar_datajud):
        usar_datajud(ProcessoFalso(*self._movimentos()))
        h = {CSRF: csrf_de(ADMIN)}
        client.post(f"/api/casos/{caso.id}/andamentos/sincronizar", headers=h)
        segunda = client.post(f"/api/casos/{caso.id}/andamentos/sincronizar", headers=h).json()
        assert (segunda["novos"], segunda["ja_existentes"]) == (0, 2)
        assert len(client.get(f"/api/casos/{caso.id}/andamentos").json()) == 2

    def test_traz_so_a_movimentacao_nova_e_preserva_o_que_foi_digitado(self, client, csrf_de, caso, usar_datajud):
        h = {CSRF: csrf_de(ADMIN)}
        client.post(f"/api/casos/{caso.id}/andamentos", headers=h, json={"titulo": "Reunião com o cliente"})
        usar_datajud(ProcessoFalso(*self._movimentos()[:2]))
        client.post(f"/api/casos/{caso.id}/andamentos/sincronizar", headers=h)
        usar_datajud(ProcessoFalso(Movimento(datetime(2026, 6, 2, tzinfo=timezone.utc), "Trânsito em julgado"), *self._movimentos()[:2]))
        terceira = client.post(f"/api/casos/{caso.id}/andamentos/sincronizar", headers=h).json()
        assert terceira["novos"] == 1
        titulos = [a["titulo"] for a in client.get(f"/api/casos/{caso.id}/andamentos").json()]
        assert "Reunião com o cliente" in titulos
        assert titulos.index("Trânsito em julgado") < titulos.index("Sentença")

    def test_importado_do_tribunal_nao_pode_ser_apagado(self, client, csrf_de, caso, usar_datajud):
        usar_datajud(ProcessoFalso(*self._movimentos()))
        h = {CSRF: csrf_de(ADMIN)}
        client.post(f"/api/casos/{caso.id}/andamentos/sincronizar", headers=h)
        importado = client.get(f"/api/casos/{caso.id}/andamentos").json()[0]
        assert client.delete(f"/api/casos/{caso.id}/andamentos/{importado['id']}", headers=h).status_code == 409

    def test_processo_nao_encontrado_no_tribunal_nao_grava_nada(self, client, csrf_de, caso, usar_datajud):
        usar_datajud(ProcessoFalso(encontrado=False))
        corpo = client.post(f"/api/casos/{caso.id}/andamentos/sincronizar", headers={CSRF: csrf_de(ADMIN)}).json()
        assert (corpo["encontrado"], corpo["novos"]) == (False, 0)
        assert "não encontrado" in corpo["mensagem"]

    def test_caso_sem_numero_de_processo_vira_422(self, client, csrf_de, criar_caso, usar_datajud):
        usar_datajud(ProcessoFalso())
        sem_numero = criar_caso(numero_processo=None)
        resp = client.post(f"/api/casos/{sem_numero.id}/andamentos/sincronizar", headers={CSRF: csrf_de(ADMIN)})
        assert resp.status_code == 422 and "número" in resp.json()["detail"]

    def test_datajud_sem_chave_configurada_vira_503(self, client, csrf_de, caso, app):
        class SemChave:
            def consultar(self, numero):
                raise IntegracaoNaoConfiguradaError("DataJud", "Chave do DataJud não configurada.")

        app.dependency_overrides[get_processo_service] = lambda: SemChave()
        resp = client.post(f"/api/casos/{caso.id}/andamentos/sincronizar", headers={CSRF: csrf_de(ADMIN)})
        assert resp.status_code == 503
