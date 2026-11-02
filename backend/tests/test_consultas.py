"""Camada de integracoes (app/integrations) e consultas publicas, tudo OFFLINE.

Estrutura do arquivo (do mais baixo nivel ao mais alto):
  1. CacheTTL e ClienteHttp (a base)         3. NumeroCNJ e DataJudClient
  2. BrasilAPI e Banco Central (clientes)     4. servicos (juros) e rotas HTTP
O `httpx.Client` e trocado por um MockTransport: nenhum teste toca a internet.
"""

import json
from datetime import date, datetime
from decimal import Decimal

import httpx
import pytest

from app.api.routes.consultas import (
    get_brasilapi,
    get_calendario_service,
    get_juros_service,
    get_processo_service,
)
from app.config import get_settings
from app.integrations.base import ClienteHttp
from app.integrations.bcb import SERIES, BancoCentralClient
from app.integrations.brasilapi import BrasilAPIClient
from app.integrations.cache import CacheTTL
from app.integrations.datajud import DataJudClient, NumeroCNJ
from app.integrations.erros import (
    DadosInvalidosError,
    IntegracaoErro,
    IntegracaoNaoConfiguradaError,
    IntegracaoNaoEncontradaError,
)
from app.services.calendario_service import CalendarioService
from app.services.juros_service import JurosService
from app.services.processo_externo_service import ProcessoExternoService
from tests.conftest import PADRAO


def _http(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _json(corpo, status=200):
    return httpx.Response(status, json=corpo)


# ============================================================== 1. a base

class TestCacheTTL:
    def test_guarda_e_devolve(self):
        c = CacheTTL()
        c.guardar("a", [1, 2], 60)
        assert c.obter("a") == [1, 2] and c.obter("nao-existe") is None

    def test_expira(self, monkeypatch):
        agora = [1000.0]
        monkeypatch.setattr("app.integrations.cache.time.monotonic", lambda: agora[0])
        c = CacheTTL()
        c.guardar("a", "x", 10)
        agora[0] = 1009
        assert c.obter("a") == "x"
        agora[0] = 1011
        assert c.obter("a") is None

    def test_descarta_o_mais_antigo_quando_cheio(self, monkeypatch):
        agora = [0.0]
        monkeypatch.setattr("app.integrations.cache.time.monotonic", lambda: agora[0])
        c = CacheTTL(max_itens=2)
        for i, chave in enumerate(("a", "b", "c")):
            agora[0] = i
            c.guardar(chave, i, 100)
        assert c.obter("a") is None and c.obter("b") == 1 and c.obter("c") == 2


class _Exemplo(ClienteHttp):
    servico = "Exemplo"

    def __init__(self, http, chave="segredo"):
        super().__init__("https://api.exemplo.test/v1", http=http)
        self._chave = chave

    def _cabecalhos(self):
        if not self._chave:
            raise self._nao_configurada()
        return {"X-Chave": self._chave}


class TestClienteHttp:
    def test_envia_url_base_e_cabecalhos_da_subclasse(self):
        vistos = []
        c = _Exemplo(_http(lambda r: (vistos.append(r), _json({"ok": 1}))[1]))
        assert c._chamar("GET", "/itens", params={"q": "a"}) == {"ok": 1}
        assert str(vistos[0].url) == "https://api.exemplo.test/v1/itens?q=a" and vistos[0].headers["x-chave"] == "segredo"

    @pytest.mark.parametrize("status,tipo", [
        (401, IntegracaoErro), (403, IntegracaoErro), (404, IntegracaoNaoEncontradaError), (429, IntegracaoErro), (500, IntegracaoErro),
    ])
    def test_erros_http_viram_integracao_erro_sem_vazar_segredo(self, status, tipo):
        c = _Exemplo(_http(lambda r: _json({"detail": "chave segredo invalida"}, status)))
        with pytest.raises(tipo) as exc:
            c._chamar("GET", "/x")
        assert exc.value.status == status
        if status in (401, 403, 404, 429):
            assert "segredo" not in exc.value.mensagem  # mensagem padrao, sem o corpo do provedor

    def test_timeout_e_rede(self):
        def lento(r):
            raise httpx.ReadTimeout("x", request=r)

        def caiu(r):
            raise httpx.ConnectError("x", request=r)

        with pytest.raises(IntegracaoErro, match="demorou"):
            _Exemplo(_http(lento))._chamar("GET", "/x")
        with pytest.raises(IntegracaoErro, match="conectar"):
            _Exemplo(_http(caiu))._chamar("GET", "/x")

    def test_resposta_que_nao_e_json(self):
        with pytest.raises(IntegracaoErro, match="inválida"):
            _Exemplo(_http(lambda r: httpx.Response(200, text="<html>")))._chamar("GET", "/x")

    def test_sem_chave_levanta_nao_configurada(self):
        with pytest.raises(IntegracaoNaoConfiguradaError):
            _Exemplo(_http(lambda r: _json({})), chave=None)._chamar("GET", "/x")

    def test_cache_evita_chamadas_repetidas(self):
        n = []
        c = _Exemplo(_http(lambda r: (n.append(1), _json({"v": len(n)}))[1]))
        a = c._chamar_com_cache("k", 60, "GET", "/x")
        b = c._chamar_com_cache("k", 60, "GET", "/x")
        assert a == b == {"v": 1} and len(n) == 1


# ======================================================= 2. BrasilAPI e BCB

FERIADOS_2026 = [
    {"date": "2026-01-01", "name": "Confraternização mundial", "type": "national"},
    {"date": "2026-04-21", "name": "Tiradentes", "type": "national"},
]


class TestBrasilAPI:
    def test_feriados_parseia_e_usa_cache(self):
        n = []
        api = BrasilAPIClient(http=_http(lambda r: (n.append(str(r.url)), _json(FERIADOS_2026))[1]))
        f = api.feriados(2026)
        api.feriados(2026)
        assert [x.data for x in f] == [date(2026, 1, 1), date(2026, 4, 21)] and f[1].nome == "Tiradentes"
        assert n == ["https://brasilapi.com.br/api/feriados/v1/2026"]

    def test_ano_invalido_nao_chama_a_api(self):
        api = BrasilAPIClient(http=_http(lambda r: pytest.fail("nao deveria chamar")))
        with pytest.raises(DadosInvalidosError):
            api.feriados(1500)

    def test_cep_valida_e_mapeia(self):
        api = BrasilAPIClient(http=_http(lambda r: _json({"cep": "48600000", "state": "BA", "city": "Paulo Afonso", "neighborhood": "Centro", "street": "Rua A"})))
        e = api.cep("48600-000")
        assert (e.cep, e.estado, e.cidade) == ("48600000", "BA", "Paulo Afonso")
        with pytest.raises(DadosInvalidosError):
            api.cep("123")

    def test_cep_inexistente_vira_nao_encontrado(self):
        api = BrasilAPIClient(http=_http(lambda r: _json({"message": "CEP nao encontrado"}, 404)))
        with pytest.raises(IntegracaoNaoEncontradaError):
            api.cep("00000000")

    def test_cnpj_valida_digito_antes_de_chamar(self):
        api = BrasilAPIClient(http=_http(lambda r: _json({"razao_social": "BANCO DO BRASIL SA", "nome_fantasia": "DIRECAO GERAL", "descricao_situacao_cadastral": "ATIVA", "municipio": "BRASILIA", "uf": "DF"})))
        e = api.cnpj("00.000.000/0001-91")
        assert e.razao_social == "BANCO DO BRASIL SA" and e.uf == "DF"
        with pytest.raises(DadosInvalidosError):
            api.cnpj("11.111.111/1111-11")

    def test_resposta_inesperada_de_feriados(self):
        api = BrasilAPIClient(http=_http(lambda r: _json({"nao": "e lista"})))
        with pytest.raises(IntegracaoErro):
            api.feriados(2026)


def _sgs(pontos):
    return lambda r: _json([{"data": d, "valor": v} for d, v in pontos])


class TestBancoCentral:
    def test_serie_monta_datas_no_formato_do_bc(self):
        vistos = []
        bc = BancoCentralClient(http=_http(lambda r: (vistos.append(r), _json([{"data": "01/06/2026", "valor": "6.47"}]))[1]))
        pontos = bc.serie(25464, date(2026, 6, 1), date(2026, 7, 1))
        assert pontos[0].valor == 6.47 and pontos[0].data == date(2026, 6, 1)
        q = vistos[0].url.params
        assert vistos[0].url.path.endswith("/bcdata.sgs.25464/dados") and q["dataInicial"] == "01/06/2026" and q["dataFinal"] == "01/07/2026"

    def test_taxa_do_mes_encontrada_e_ainda_nao_divulgada(self):
        bc = BancoCentralClient(http=_http(_sgs([("01/06/2026", "6.47")])))
        assert bc.taxa_do_mes("credito-pessoal-nao-consignado", 2026, 6).valor == 6.47
        vazio = BancoCentralClient(http=_http(lambda r: _json([])))
        assert vazio.taxa_do_mes("credito-pessoal-nao-consignado", 2030, 1) is None

    def test_virada_de_ano_pede_o_intervalo_certo(self):
        vistos = []
        bc = BancoCentralClient(http=_http(lambda r: (vistos.append(r), _json([]))[1]))
        bc.taxa_do_mes("pf-total", 2025, 12)
        assert vistos[0].url.params["dataFinal"] == "01/01/2026"

    def test_serie_desconhecida_e_mes_invalido(self):
        bc = BancoCentralClient(http=_http(lambda r: pytest.fail("nao deveria chamar")))
        with pytest.raises(DadosInvalidosError):
            bc.taxa_do_mes("nao-existe", 2026, 1)
        with pytest.raises(DadosInvalidosError):
            bc.taxa_do_mes("pf-total", 2026, 13)

    def test_registro_de_series_e_consistente(self):
        assert SERIES["credito-pessoal-nao-consignado"].codigo == 25464
        assert len({s.codigo for s in SERIES.values()}) == len(SERIES)  # nenhum codigo repetido


# ============================================== 3. numero CNJ e DataJud

def _cnj(justica="8", tr="05", ano="2024", seq="0001234", origem="0001") -> str:
    dv = NumeroCNJ(seq, "00", ano, justica, tr, origem).digito_esperado()
    return f"{seq}-{dv}.{ano}.{justica}.{tr}.{origem}"


class TestNumeroCNJ:
    def test_valido_e_formata(self):
        n = NumeroCNJ.de_texto(_cnj())
        assert n.formatado == _cnj() and len(n.digitos) == 20

    def test_aceita_sem_pontuacao(self):
        assert NumeroCNJ.de_texto(_cnj().replace("-", "").replace(".", "")).formatado == _cnj()

    @pytest.mark.parametrize("texto", ["", "123", "0001234-00.2024.8.05.0001", "abc"])
    def test_invalido(self, texto):
        with pytest.raises(DadosInvalidosError):
            NumeroCNJ.de_texto(texto)

    @pytest.mark.parametrize("justica,tr,esperado", [
        ("8", "05", "tjba"), ("8", "07", "tjdft"), ("8", "26", "tjsp"),
        ("5", "05", "trt5"), ("5", "00", "tst"), ("4", "01", "trf1"), ("3", "00", "stj"),
    ])
    def test_descobre_o_tribunal(self, justica, tr, esperado):
        assert NumeroCNJ.de_texto(_cnj(justica=justica, tr=tr)).indice_datajud() == esperado

    @pytest.mark.parametrize("justica,tr", [("6", "05"), ("8", "00"), ("5", "25"), ("4", "09")])
    def test_tribunal_nao_suportado(self, justica, tr):
        with pytest.raises(DadosInvalidosError):
            NumeroCNJ.de_texto(_cnj(justica=justica, tr=tr)).indice_datajud()


RESPOSTA_DATAJUD = {"hits": {"hits": [{"_source": {
    "numeroProcesso": "00012346220248050001", "tribunal": "TJBA", "grau": "G1",
    "classe": {"nome": "Procedimento Comum Cível"}, "assuntos": [{"nome": "Revisão do Contrato"}],
    "orgaoJulgador": {"nome": "1ª Vara Cível de Paulo Afonso"}, "dataAjuizamento": "20240310000000",
    "movimentos": [
        {"nome": "Distribuição", "dataHora": "2024-03-10T12:00:00.000Z"},
        {"nome": "Conclusos para despacho", "dataHora": "2024-05-02T09:30:00.000Z", "complementosTabelados": [{"nome": "Urgente"}]},
    ],
}}]}}


class TestDataJud:
    def test_consulta_correta_e_ordem_dos_movimentos(self):
        vistos = []
        dj = DataJudClient("chave-publica", http=_http(lambda r: (vistos.append(r), _json(RESPOSTA_DATAJUD))[1]))
        [p] = dj.consultar(NumeroCNJ.de_texto(_cnj()))
        req = vistos[0]
        assert req.method == "POST" and req.url.path == "/api_publica_tjba/_search"
        assert req.headers["authorization"] == "APIKey chave-publica"
        assert json.loads(req.content)["query"]["match"]["numeroProcesso"] == _cnj().replace("-", "").replace(".", "")
        assert p.classe == "Procedimento Comum Cível" and p.assuntos == ("Revisão do Contrato",)
        assert [m.nome for m in p.movimentos] == ["Conclusos para despacho", "Distribuição"]  # mais recente primeiro
        assert p.movimentos[0].complemento == "Urgente" and p.data_ajuizamento == datetime(2024, 3, 10)

    def test_sem_chave_configurada(self):
        with pytest.raises(IntegracaoNaoConfiguradaError):
            DataJudClient(None, http=_http(lambda r: _json({}))).consultar(NumeroCNJ.de_texto(_cnj()))

    def test_nao_encontrado_devolve_lista_vazia(self):
        dj = DataJudClient("k", http=_http(lambda r: _json({"hits": {"hits": []}})))
        assert dj.consultar(NumeroCNJ.de_texto(_cnj())) == []

    def test_resposta_inesperada(self):
        with pytest.raises(IntegracaoErro):
            DataJudClient("k", http=_http(lambda r: _json({"x": 1}))).consultar(NumeroCNJ.de_texto(_cnj()))

    def test_repete_consulta_so_uma_vez_por_cinco_minutos(self):
        n = []
        dj = DataJudClient("k", http=_http(lambda r: (n.append(1), _json(RESPOSTA_DATAJUD))[1]))
        numero = NumeroCNJ.de_texto(_cnj())
        dj.consultar(numero)
        dj.consultar(numero)
        assert len(n) == 1


# ===================================================== 4. servicos e rotas

class TestJurosService:
    def _servico(self, valor="6.47"):
        return JurosService(BancoCentralClient(http=_http(_sgs([("01/06/2026", valor)]))))

    @pytest.mark.parametrize("taxa,faixa", [
        ("5.00", "Igual ou abaixo da média de mercado"),
        ("8.00", "Acima da média (até 1,5 vez)"),
        ("12.50", "Entre 1,5 e 2 vezes a média"),
        ("19.00", "Entre 2 e 3 vezes a média"),
        ("25.00", "Mais de 3 vezes a média"),
    ])
    def test_faixas(self, taxa, faixa):
        c = self._servico().comparar("credito-pessoal-nao-consignado", date(2026, 6, 10), Decimal(taxa))
        assert c.faixa == faixa and c.taxa_media_mensal == Decimal("6.47")

    def test_numeros_da_comparacao(self):
        c = self._servico().comparar("credito-pessoal-nao-consignado", date(2026, 6, 10), Decimal("12.94"))
        assert c.razao == Decimal("2.00") and c.diferenca_pontos == Decimal("6.47") and c.acima_da_media
        assert c.taxa_media_anual == Decimal("112.19")  # (1,0647^12 - 1)

    def test_equivalente_anual_composto(self):
        c = self._servico("5.00").comparar("credito-pessoal-nao-consignado", date(2026, 6, 10), Decimal("5.00"))
        assert c.taxa_contrato_anual == Decimal("79.59")

    def test_mes_ainda_nao_divulgado(self):
        s = JurosService(BancoCentralClient(http=_http(lambda r: _json([]))))
        with pytest.raises(IntegracaoNaoEncontradaError):
            s.comparar("credito-pessoal-nao-consignado", date(2026, 6, 10), Decimal("5"))

    def test_entradas_invalidas(self):
        s = self._servico()
        with pytest.raises(DadosInvalidosError):
            s.comparar("credito-pessoal-nao-consignado", date(2999, 1, 1), Decimal("5"))
        with pytest.raises(DadosInvalidosError):
            s.comparar("credito-pessoal-nao-consignado", date(2026, 6, 1), Decimal("0"))


class TestRotasConsultas:
    BASE = "/api/consultas"

    @pytest.fixture()
    def instalar(self, app):
        def _instalar(*, brasilapi=None, bcb=None, datajud=None):
            if brasilapi:
                api = BrasilAPIClient(http=_http(brasilapi))
                app.dependency_overrides[get_brasilapi] = lambda: api
                app.dependency_overrides[get_calendario_service] = lambda: CalendarioService(api)
            if bcb:
                app.dependency_overrides[get_juros_service] = lambda: JurosService(BancoCentralClient(http=_http(bcb)))
            if datajud:
                app.dependency_overrides[get_processo_service] = lambda: ProcessoExternoService(datajud)
        return _instalar

    def test_exigem_login(self, client):
        for caminho in ("/feriados/2026", "/cep/48600000", "/cnpj/00000000000191", "/juros/series", "/processos/00012346220248050001"):
            assert client.get(self.BASE + caminho).status_code == 401

    def test_feriados_de_varios_anos(self, client, csrf_de, instalar):
        instalar(brasilapi=lambda r: _json([{"date": f"{r.url.path[-4:]}-01-01", "name": "Ano Novo", "type": "national"}]))
        csrf_de(PADRAO)
        corpo = client.get(f"{self.BASE}/feriados/2026?anos=2").json()
        assert [f["data"] for f in corpo] == ["2026-01-01", "2027-01-01"]

    def test_cep_e_cnpj(self, client, csrf_de, instalar):
        def api(r):
            if "/cep/" in r.url.path:
                return _json({"state": "BA", "city": "Paulo Afonso", "neighborhood": "Centro", "street": "Rua A"})
            return _json({"razao_social": "EMPRESA X", "descricao_situacao_cadastral": "ATIVA", "municipio": "SALVADOR", "uf": "BA"})

        instalar(brasilapi=api)
        csrf_de(PADRAO)
        assert client.get(f"{self.BASE}/cep/48600-000").json()["cidade"] == "Paulo Afonso"
        assert client.get(f"{self.BASE}/cnpj/00000000000191").json()["razao_social"] == "EMPRESA X"
        assert client.get(f"{self.BASE}/cnpj/11111111111111").status_code == 422

    def test_lista_de_series(self, client, csrf_de, instalar):
        instalar(bcb=_sgs([]))
        csrf_de(PADRAO)
        slugs = {s["slug"] for s in client.get(f"{self.BASE}/juros/series").json()}
        assert "credito-pessoal-nao-consignado" in slugs

    def test_comparar_juros(self, client, csrf_de, instalar):
        instalar(bcb=_sgs([("01/06/2026", "6.47")]))
        csrf = csrf_de(PADRAO)
        r = client.post(f"{self.BASE}/juros/comparar", headers={"X-CSRF-Token": csrf},
                        json={"serie": "credito-pessoal-nao-consignado", "data_contrato": "2026-06-10", "taxa_contrato_mensal": "12.94"})
        corpo = r.json()
        assert r.status_code == 200 and corpo["razao"] == "2.00" and corpo["fonte"].startswith("Banco Central")
        assert corpo["serie"]["slug"] == "credito-pessoal-nao-consignado" and "caso a caso" in corpo["aviso"]

    @pytest.mark.parametrize("corpo,status", [
        ({"serie": "x", "data_contrato": "2026-06-10", "taxa_contrato_mensal": "5"}, 422),  # serie desconhecida
        ({"serie": "pf-total", "data_contrato": "2026-06-10", "taxa_contrato_mensal": "0"}, 422),
        ({"serie": "pf-total", "data_contrato": "2026-06-10", "taxa_contrato_mensal": "5", "extra": 1}, 422),
    ])
    def test_comparar_juros_entradas_invalidas(self, client, csrf_de, instalar, corpo, status):
        instalar(bcb=_sgs([("01/06/2026", "6.47")]))
        r = client.post(f"{self.BASE}/juros/comparar", headers={"X-CSRF-Token": csrf_de(PADRAO)}, json=corpo)
        assert r.status_code == status

    def test_comparar_mes_nao_divulgado_e_404(self, client, csrf_de, instalar):
        instalar(bcb=lambda r: _json([]))
        r = client.post(f"{self.BASE}/juros/comparar", headers={"X-CSRF-Token": csrf_de(PADRAO)},
                        json={"serie": "pf-total", "data_contrato": "2026-06-10", "taxa_contrato_mensal": "5"})
        assert r.status_code == 404 and "ainda não divulgou" in r.json()["detail"]

    def test_processo_encontrado(self, client, csrf_de, instalar):
        instalar(datajud=DataJudClient("k", http=_http(lambda r: _json(RESPOSTA_DATAJUD))))
        csrf_de(PADRAO)
        corpo = client.get(f"{self.BASE}/processos/{_cnj()}").json()
        assert corpo["encontrado"] and corpo["tribunal"] == "tjba" and corpo["instancias"][0]["movimentos"][0]["nome"] == "Conclusos para despacho"
        assert corpo["fonte"] == "DataJud - CNJ"

    def test_processo_nao_encontrado_nao_e_erro(self, client, csrf_de, instalar):
        instalar(datajud=DataJudClient("k", http=_http(lambda r: _json({"hits": {"hits": []}}))))
        csrf_de(PADRAO)
        corpo = client.get(f"{self.BASE}/processos/{_cnj()}").json()
        assert corpo["encontrado"] is False and corpo["instancias"] == []

    def test_processo_numero_invalido_422_e_sem_chave_503(self, client, csrf_de, instalar):
        instalar(datajud=DataJudClient(None, http=_http(lambda r: _json({}))))
        csrf_de(PADRAO)
        assert client.get(f"{self.BASE}/processos/0001234-00.2024.8.05.0001").status_code == 422
        assert client.get(f"{self.BASE}/processos/{_cnj()}").status_code == 503

    def test_servico_externo_fora_do_ar_vira_502(self, client, csrf_de, instalar):
        instalar(brasilapi=lambda r: httpx.Response(500))
        csrf_de(PADRAO)
        assert client.get(f"{self.BASE}/feriados/2026").status_code == 502

    def test_limite_de_consultas_por_usuario(self, client, csrf_de, instalar, monkeypatch):
        from app.api.routes import consultas as rota

        monkeypatch.setattr(rota.settings, "consultas_limite_minuto", 2)
        instalar(brasilapi=lambda r: _json(FERIADOS_2026))
        csrf_de(PADRAO)
        assert client.get(f"{self.BASE}/feriados/2026").status_code == 200
        assert client.get(f"{self.BASE}/feriados/2026").status_code == 200
        assert client.get(f"{self.BASE}/feriados/2026").status_code == 429

    def test_chave_do_datajud_nunca_vaza_na_resposta(self, client, csrf_de, instalar):
        instalar(datajud=DataJudClient("chave-secreta-xyz", http=_http(lambda r: httpx.Response(403, json={"msg": "chave-secreta-xyz"}))))
        csrf_de(PADRAO)
        r = client.get(f"{self.BASE}/processos/{_cnj()}")
        assert r.status_code == 502 and "chave-secreta-xyz" not in r.text
