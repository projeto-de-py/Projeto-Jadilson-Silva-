"""Reconhecedor de entidades jurídicas (NER): tokenização, agrupamento, endpoint e privacidade.

Os testes treinam um modelo MINÚSCULO na hora (frases de brinquedo): assim não dependem do
arquivo ai-model/models/ner_juridico.joblib nem do LeNER-Br. A qualidade do modelo real é
medida por ai-model/scripts/treinar_ner.py (métricas em ai-model/models/metricas_ner.json).
"""

import pytest

from app.api.routes import ia as rota_ia
from app.ia.ner.reconhecedor import ReconhecedorEntidades, agrupar_entidades, faixa_de_confianca
from app.ia.ner.servico import ModeloIndisponivelError, ServicoEntidades
from app.ia.ner.tokenizador import tokenizar
from tests.conftest import PADRAO

pytest.importorskip("sklearn")  # o modelo precisa do scikit-learn

CSRF = "X-CSRF-Token"

# Frases de brinquedo: nomes após "Sr." e leis após "art." para o modelo ter o que aprender.
FRASES = [
    (["O", "Sr", ".", "Carlos", "Silva", "recorreu", "."], ["O", "O", "O", "B-PESSOA", "I-PESSOA", "O", "O"]),
    (["A", "Sra", ".", "Maria", "Souza", "compareceu", "."], ["O", "O", "O", "B-PESSOA", "I-PESSOA", "O", "O"]),
    (["O", "Sr", ".", "Pedro", "Lima", "assinou", "."], ["O", "O", "O", "B-PESSOA", "I-PESSOA", "O", "O"]),
    (["Conforme", "o", "art", ".", "5", "da", "CLT", "."], ["O", "O", "O", "O", "O", "O", "B-LEGISLACAO", "O"]),
    (["Conforme", "o", "art", ".", "7", "da", "CLT", "."], ["O", "O", "O", "O", "O", "O", "B-LEGISLACAO", "O"]),
] * 6


@pytest.fixture(scope="module")
def modelo_pequeno():
    return ReconhecedorEntidades(conjunto="completo", alpha=1e-5, min_freq=1, max_iter=50).treinar(FRASES)


@pytest.fixture()
def servico_com_modelo(tmp_path, modelo_pequeno, monkeypatch):
    caminho = tmp_path / "ner_teste.joblib"
    modelo_pequeno.salvar(caminho)
    servico = ServicoEntidades(caminho)
    monkeypatch.setattr(rota_ia, "obter_servico_ner", lambda: servico)
    return servico


class TestTokenizador:
    def test_data_e_numero_de_processo_ficam_em_um_token_e_pontuacao_separa(self):
        palavras = [t.texto for t in tokenizar("art. 178, II, em 14/11/2017 (proc. 1.0024.13.385589-0/001)")]
        assert palavras[:4] == ["art", ".", "178", ","]
        assert "14/11/2017" in palavras
        assert "1.0024.13.385589-0/001" in palavras

    def test_posicoes_apontam_para_o_texto_original(self):
        texto = "Lei 8.213 de 1991"
        for t in tokenizar(texto):
            assert texto[t.inicio : t.fim] == t.texto


class TestAgrupamento:
    def test_junta_B_e_I_do_mesmo_tipo_e_separa_entidades_vizinhas(self):
        texto = "João Silva Maria"
        etiquetas = [("B-PESSOA", 0.9), ("I-PESSOA", 0.7), ("B-PESSOA", 0.8)]
        achadas = agrupar_entidades(etiquetas, tokenizar(texto), texto)
        assert [e.texto for e in achadas] == ["João Silva", "Maria"]
        assert achadas[0].confianca == pytest.approx(0.8)  # média das palavras

    def test_I_sem_B_antes_comeca_uma_entidade_nova(self):
        texto = "a Pedro"
        achadas = agrupar_entidades([("O", 0.99), ("I-PESSOA", 0.6)], tokenizar(texto), texto)
        assert len(achadas) == 1 and achadas[0].tipo == "PESSOA"

    def test_faixas_de_confianca(self):
        assert faixa_de_confianca(0.97) == "alta"
        assert faixa_de_confianca(0.75) == "media"
        assert faixa_de_confianca(0.30) == "baixa"


class TestModelo:
    def test_reconhece_o_que_aprendeu_com_posicao_correta(self, modelo_pequeno):
        texto = "O Sr. Carlos Silva citou o art. 5 da CLT."
        achadas = modelo_pequeno.extrair(texto)
        tipos = {e.tipo: texto[e.inicio : e.fim] for e in achadas}
        assert tipos.get("PESSOA") == "Carlos Silva"
        assert tipos.get("LEGISLACAO") == "CLT"
        assert all(0 <= e.confianca <= 1 for e in achadas)

    def test_texto_sem_entidades_devolve_lista_vazia(self, modelo_pequeno):
        assert modelo_pequeno.extrair("") == []

    def test_treino_e_reproduzivel_com_a_mesma_semente(self):
        a = ReconhecedorEntidades(min_freq=1, max_iter=20).treinar(FRASES)
        b = ReconhecedorEntidades(min_freq=1, max_iter=20).treinar(FRASES)
        assert a.etiquetar(["Sr", ".", "Carlos"]) == b.etiquetar(["Sr", ".", "Carlos"])


class TestServico:
    def test_mascara_pessoas_e_preserva_o_resto(self, servico_com_modelo):
        saida = servico_com_modelo.mascarar_nomes("O Sr. Carlos Silva citou o art. 5 da CLT.", confianca_minima=0.0)
        assert "Carlos Silva" not in saida and "[NOME]" in saida and "CLT" in saida

    def test_modelo_ausente_gera_erro_claro(self, tmp_path):
        servico = ServicoEntidades(tmp_path / "nao_existe.joblib")
        assert servico.disponivel() is False
        with pytest.raises(ModeloIndisponivelError, match="treinar_ner"):
            servico.extrair("texto")


class TestEndpoint:
    def test_exige_login(self, client):
        assert client.post("/api/ia/entidades", json={"texto": "x"}).status_code in (401, 403)

    def test_exige_csrf(self, client, advogada, fazer_login):
        fazer_login(PADRAO["email"], PADRAO["senha"])
        assert client.post("/api/ia/entidades", json={"texto": "O Sr. Carlos Silva"}).status_code == 403

    def test_devolve_entidades_com_confianca_e_faixa(self, client, advogada, csrf_de, servico_com_modelo):
        corpo = client.post("/api/ia/entidades", headers={CSRF: csrf_de(PADRAO)}, json={"texto": "O Sr. Carlos Silva citou o art. 5 da CLT."})
        assert corpo.status_code == 200
        dados = corpo.json()
        assert dados["contagem"].get("PESSOA") == 1
        assert {"tipo", "texto", "inicio", "fim", "confianca", "faixa"} <= set(dados["entidades"][0])
        assert dados["versao_modelo"].startswith("ner-")
        assert "aviso" in dados

    @pytest.mark.parametrize("texto", ["", "   ", "x" * 20_001])
    def test_texto_invalido_vira_422(self, client, advogada, csrf_de, servico_com_modelo, texto):
        resp = client.post("/api/ia/entidades", headers={CSRF: csrf_de(PADRAO)}, json={"texto": texto})
        assert resp.status_code == 422

    def test_modelo_ausente_vira_503_com_instrucao(self, client, advogada, csrf_de, tmp_path, monkeypatch):
        vazio = ServicoEntidades(tmp_path / "nao_existe.joblib")
        monkeypatch.setattr(rota_ia, "obter_servico_ner", lambda: vazio)
        resp = client.post("/api/ia/entidades", headers={CSRF: csrf_de(PADRAO)}, json={"texto": "O Sr. Carlos"})
        assert resp.status_code == 503 and "treinar_ner" in resp.json()["detail"]

    def test_campo_desconhecido_vira_422(self, client, advogada, csrf_de, servico_com_modelo):
        resp = client.post("/api/ia/entidades", headers={CSRF: csrf_de(PADRAO)}, json={"texto": "O Sr. Carlos", "extra": "x"})
        assert resp.status_code == 422


class TestProtecaoNoFluxoDaIA:
    def test_com_a_opcao_ligada_o_nome_nao_chega_ao_provedor(self, servico_com_modelo, monkeypatch):
        from app.config import get_settings
        from app.ia import servico as servico_ia

        monkeypatch.setattr(get_settings(), "ia_mascarar_nomes", True)
        monkeypatch.setattr(servico_ia, "obter_servico_ner", lambda: servico_com_modelo)
        monkeypatch.setattr(servico_com_modelo, "mascarar_nomes", lambda t, **k: t.replace("Carlos Silva", "[NOME]"))
        protegido = servico_ia._proteger("O Sr. Carlos Silva, CPF 123.456.789-09")
        assert "Carlos Silva" not in protegido and "123.456.789-09" not in protegido

    def test_com_a_opcao_desligada_so_a_regra_atua(self, monkeypatch):
        from app.config import get_settings
        from app.ia import servico as servico_ia

        monkeypatch.setattr(get_settings(), "ia_mascarar_nomes", False)
        assert "Carlos" in servico_ia._proteger("O Sr. Carlos, CPF 123.456.789-09")
