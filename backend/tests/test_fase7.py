"""Testes da Fase 6/RF06: andamentos juridicos (historico de movimentacoes).

Cobrem as regras de negocio exigidas: registro com responsavel SEMPRE da
sessao autenticada (payload `extra="forbid"` nao aceita `criado_por`/`caso_id`),
escopo de acesso por caso (404 sem vazar a existencia de casos restritos),
permissao granular de escrita (`pode_registrar_andamento` - 403 sem a
concessao), caso arquivado sem novos registros (422), consulta paginada no
banco ordenada por `ocorrido_em` (asc/desc), detalhe restrito ao caso da URL,
horario local de Brasilia (fuso convertido, naive assumido local),
IMUTABILIDADE do historico (nao existem rotas de edicao/exclusao - correcao
por registro complementar) e ATOMICIDADE do registro (falha = nada persiste).
"""

from datetime import datetime, timedelta

import pytest

from app.core.tempo import agora_brasilia
from tests.conftest import ADMIN, FUNCIONARIO, PADRAO

CSRF = "X-CSRF-Token"


def _criar_andamento(client, csrf, caso_id, **dados):
    """Registra um andamento (201) com titulo padrao."""
    payload = {"titulo": "Andamento da Fase 6"}
    payload.update(dados)
    resp = client.post(
        f"/api/casos/{caso_id}/andamentos",
        headers={CSRF: csrf},
        json=payload,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _falha_apos_flush(self, andamento):
    """Simula falha APOS o flush (teste de atomicidade do registro)."""
    self.db.add(andamento)
    self.db.flush()
    raise RuntimeError("falha simulada no registro")


# --------------------------------------------------------------- cadastro


class TestCadastroAndamento:
    def test_registrar_201_com_responsavel_da_sessao(
        self, client, csrf_de, criar_caso, admin
    ):
        caso = criar_caso()
        item = _criar_andamento(
            client, csrf_de(ADMIN), caso.id,
            descricao="Distribuicao da peticao inicial",
        )
        assert item["caso_id"] == caso.id
        assert item["titulo"] == "Andamento da Fase 6"
        assert item["descricao"] == "Distribuicao da peticao inicial"
        # responsavel e SEMPRE o operador autenticado (sessao, nao payload)
        assert item["criado_por"] == admin.id
        assert item["criado_por_nome"] == "Jadilson Silva"
        assert item["id"] > 0

    def test_payload_nao_aceita_criado_por(self, client, csrf_de, criar_caso):
        caso = criar_caso()
        resp = client.post(
            f"/api/casos/{caso.id}/andamentos",
            headers={CSRF: csrf_de(ADMIN)},
            json={
                "titulo": "Tentativa de forjar auditoria",
                "criado_por": 9999,
            },
        )
        assert resp.status_code == 422, resp.text  # extra="forbid"

    def test_payload_nao_aceita_caso_id_nem_id(
        self, client, csrf_de, criar_caso
    ):
        caso = criar_caso()
        resp = client.post(
            f"/api/casos/{caso.id}/andamentos",
            headers={CSRF: csrf_de(ADMIN)},
            json={"titulo": "Campos proibidos", "caso_id": caso.id, "id": 1},
        )
        assert resp.status_code == 422, resp.text  # extra="forbid"

    def test_titulo_minimo_3_caracteres(self, client, csrf_de, criar_caso):
        caso = criar_caso()
        resp = client.post(
            f"/api/casos/{caso.id}/andamentos",
            headers={CSRF: csrf_de(ADMIN)},
            json={"titulo": "ab"},
        )
        assert resp.status_code == 422, resp.text

    def test_ocorrido_em_ausente_usa_agora_local(
        self, client, csrf_de, criar_caso
    ):
        caso = criar_caso()
        antes = agora_brasilia()
        item = _criar_andamento(client, csrf_de(ADMIN), caso.id)
        depois = agora_brasilia()
        ocorrido = datetime.fromisoformat(item["ocorrido_em"])
        assert ocorrido.tzinfo is None, "horario local deve ser naive"
        assert antes <= ocorrido <= depois

    def test_ocorrido_em_com_fuso_e_convertido_para_brasilia(
        self, client, csrf_de, criar_caso
    ):
        caso = criar_caso()
        item = _criar_andamento(
            client, csrf_de(ADMIN), caso.id,
            ocorrido_em="2026-03-10T12:00:00+00:00",  # UTC
        )
        # Brasilia = UTC-3: 12:00 UTC vira 09:00 local
        assert item["ocorrido_em"] == "2026-03-10T09:00:00"

    def test_ocorrido_em_naive_e_assumido_local(
        self, client, csrf_de, criar_caso
    ):
        caso = criar_caso()
        item = _criar_andamento(
            client, csrf_de(ADMIN), caso.id,
            ocorrido_em="2026-03-10T12:00:00",  # sem fuso
        )
        assert item["ocorrido_em"] == "2026-03-10T12:00:00"

    def test_caso_arquivado_nao_recebe_andamento_422(
        self, client, csrf_de, criar_caso
    ):
        caso = criar_caso(arquivado=True)
        resp = client.post(
            f"/api/casos/{caso.id}/andamentos",
            headers={CSRF: csrf_de(ADMIN)},
            json={"titulo": "Movimentacao posterior ao arquivamento"},
        )
        assert resp.status_code == 422, resp.text

    def test_caso_inexistente_404(self, client, csrf_de):
        resp = client.post(
            "/api/casos/999999/andamentos",
            headers={CSRF: csrf_de(ADMIN)},
            json={"titulo": "Caso que nao existe"},
        )
        assert resp.status_code == 404, resp.text

    def test_post_sem_csrf_403(self, client, csrf_de, criar_caso):
        caso = criar_caso()
        csrf_de(ADMIN)  # sessao valida, mas sem o header CSRF
        resp = client.post(
            f"/api/casos/{caso.id}/andamentos",
            json={"titulo": "Sem token CSRF"},
        )
        assert resp.status_code == 403, resp.text

    def test_sem_sessao_401(self, client, criar_caso):
        caso = criar_caso()
        resp = client.post(
            f"/api/casos/{caso.id}/andamentos",
            json={"titulo": "Anonimo"},
        )
        assert resp.status_code == 401, resp.text


# ------------------------------------------------------- escopo/permissao


class TestEscopoEPermissao:
    def test_listar_fora_do_escopo_404(self, client, csrf_de, criar_caso):
        caso = criar_caso()  # caso do admin; advogada nao tem acesso
        csrf_de(PADRAO)
        resp = client.get(f"/api/casos/{caso.id}/andamentos")
        assert resp.status_code == 404, resp.text  # nunca 200 vazio nem 403

    def test_detalhe_fora_do_escopo_404(self, client, csrf_de, criar_caso):
        caso = criar_caso()
        item = _criar_andamento(client, csrf_de(ADMIN), caso.id)
        csrf_de(PADRAO)
        resp = client.get(
            f"/api/casos/{caso.id}/andamentos/{item['id']}"
        )
        assert resp.status_code == 404, resp.text

    def test_registrar_fora_do_escopo_404(self, client, csrf_de, criar_caso):
        caso = criar_caso()
        resp = client.post(
            f"/api/casos/{caso.id}/andamentos",
            headers={CSRF: csrf_de(PADRAO)},
            json={"titulo": "Fora do escopo"},
        )
        assert resp.status_code == 404, resp.text

    def test_funcionario_com_acesso_sem_permissao_403(
        self, client, csrf_de, criar_caso, conceder_acesso, funcionario
    ):
        caso = criar_caso()
        conceder_acesso(caso, funcionario)  # so pode_visualizar
        resp = client.post(
            f"/api/casos/{caso.id}/andamentos",
            headers={CSRF: csrf_de(FUNCIONARIO)},
            json={"titulo": "Sem grant de andamento"},
        )
        assert resp.status_code == 403, resp.text

    def test_funcionario_com_grant_registra_201(
        self, client, csrf_de, criar_caso, conceder_acesso, funcionario
    ):
        caso = criar_caso()
        conceder_acesso(caso, funcionario, pode_registrar_andamento=True)
        item = _criar_andamento(
            client, csrf_de(FUNCIONARIO), caso.id,
            titulo="Movimentacao do funcionario",
        )
        assert item["criado_por"] == funcionario.id
        assert item["criado_por_nome"] == "Felipe Funcionario"

    def test_funcionario_com_acesso_le_a_lista(
        self, client, csrf_de, criar_caso, conceder_acesso, funcionario
    ):
        caso = criar_caso()
        _criar_andamento(client, csrf_de(ADMIN), caso.id)
        conceder_acesso(caso, funcionario)  # leitura sem grant de escrita
        resp = client.get(
            f"/api/casos/{caso.id}/andamentos",
            headers={CSRF: csrf_de(FUNCIONARIO)},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["total"] == 1

    def test_responsavel_do_caso_registra_201(
        self, client, csrf_de, criar_cliente, advogada
    ):
        # caso criado VIA API: o service concede acesso ao responsavel
        # (mesmo fluxo do teste de responsavel da Fase 4)
        cliente = criar_cliente(nome="Resp andamento")
        resp_caso = client.post(
            "/api/casos",
            headers={CSRF: csrf_de(ADMIN)},
            json={
                "titulo": "Caso da responsavel",
                "cliente_id": cliente.id,
                "responsavel_id": advogada.id,
            },
        )
        assert resp_caso.status_code == 201, resp_caso.text
        item = _criar_andamento(
            client, csrf_de(PADRAO), resp_caso.json()["id"],
            titulo="Movimentacao da responsavel",
        )
        assert item["criado_por"] == advogada.id

    def test_linha_revogada_perde_acesso_404(
        self, client, csrf_de, criar_caso, conceder_acesso, funcionario
    ):
        caso = criar_caso()
        _criar_andamento(client, csrf_de(ADMIN), caso.id)
        conceder_acesso(caso, funcionario, ativo=False)  # revogada
        resp = client.get(
            f"/api/casos/{caso.id}/andamentos",
            headers={CSRF: csrf_de(FUNCIONARIO)},
        )
        assert resp.status_code == 404, resp.text

    def test_caso_arquivado_continua_consultavel(
        self, client, csrf_de, criar_caso, db_session
    ):
        from app.models.caso import Caso

        caso = criar_caso()
        _criar_andamento(client, csrf_de(ADMIN), caso.id)
        caso.arquivado = True  # soft delete depois do registro
        db_session.commit()

        resp = client.get(
            f"/api/casos/{caso.id}/andamentos",
            headers={CSRF: csrf_de(ADMIN)},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["total"] == 1  # historico permanece consultavel


# -------------------------------------------------------------- consulta


class TestConsultaAndamento:
    @staticmethod
    def _criar_cronologico(client, csrf, caso_id):
        """Tres andamentos com datas DISTINTAS (ordem deterministica)."""
        base = datetime(2026, 3, 1, 9, 0)
        criados = []
        for dia in (1, 2, 3):
            criados.append(
                _criar_andamento(
                    client, csrf, caso_id,
                    titulo=f"Movimentacao dia {dia}",
                    ocorrido_em=(base + timedelta(days=dia)).isoformat(),
                )
            )
        return criados

    def test_listar_desc_padrao_mais_recente_primeiro(
        self, client, csrf_de, criar_caso
    ):
        caso = criar_caso()
        self._criar_cronologico(client, csrf_de(ADMIN), caso.id)
        resp = client.get(f"/api/casos/{caso.id}/andamentos")
        assert resp.status_code == 200, resp.text
        corpo = resp.json()
        assert corpo["total"] == 3
        titulos = [i["titulo"] for i in corpo["itens"]]
        assert titulos == [
            "Movimentacao dia 3",
            "Movimentacao dia 2",
            "Movimentacao dia 1",
        ]

    def test_listar_asc_cronologia_invertida(
        self, client, csrf_de, criar_caso
    ):
        caso = criar_caso()
        self._criar_cronologico(client, csrf_de(ADMIN), caso.id)
        resp = client.get(f"/api/casos/{caso.id}/andamentos?ordem=asc")
        assert resp.status_code == 200, resp.text
        titulos = [i["titulo"] for i in resp.json()["itens"]]
        assert titulos == [
            "Movimentacao dia 1",
            "Movimentacao dia 2",
            "Movimentacao dia 3",
        ]

    def test_ordem_invalida_422(self, client, csrf_de, criar_caso):
        caso = criar_caso()
        resp = client.get(
            f"/api/casos/{caso.id}/andamentos?ordem=later",
            headers={CSRF: csrf_de(ADMIN)},
        )
        assert resp.status_code == 422, resp.text

    def test_paginacao_no_banco(self, client, csrf_de, criar_caso):
        caso = criar_caso()
        self._criar_cronologico(client, csrf_de(ADMIN), caso.id)
        _criar_andamento(
            client, csrf_de(ADMIN), caso.id,
            titulo="Movimentacao dia 4",
            ocorrido_em=datetime(2026, 3, 4, 9, 0).isoformat(),
        )
        _criar_andamento(
            client, csrf_de(ADMIN), caso.id,
            titulo="Movimentacao dia 5",
            ocorrido_em=datetime(2026, 3, 5, 9, 0).isoformat(),
        )
        resp = client.get(
            f"/api/casos/{caso.id}/andamentos?pagina=2&limite=2&ordem=asc"
        )
        assert resp.status_code == 200, resp.text
        corpo = resp.json()
        assert corpo["total"] == 5
        assert corpo["pagina"] == 2
        assert corpo["limite"] == 2
        assert len(corpo["itens"]) == 2
        # pagina 2 em ordem ascendente: dias 3 e 4
        assert [i["titulo"] for i in corpo["itens"]] == [
            "Movimentacao dia 3",
            "Movimentacao dia 4",
        ]

    def test_lista_filtra_por_caso(self, client, csrf_de, criar_caso):
        caso_a = criar_caso(cliente="Caso A")
        caso_b = criar_caso(cliente="Caso B")
        csrf = csrf_de(ADMIN)
        _criar_andamento(client, csrf, caso_a.id, titulo="Do caso A 1")
        _criar_andamento(client, csrf, caso_a.id, titulo="Do caso A 2")
        _criar_andamento(client, csrf, caso_b.id, titulo="Do caso B 1")

        resp = client.get(f"/api/casos/{caso_a.id}/andamentos")
        corpo = resp.json()
        assert corpo["total"] == 2
        assert all(i["caso_id"] == caso_a.id for i in corpo["itens"])

    def test_detalhe_expoe_todos_os_campos(
        self, client, csrf_de, criar_caso
    ):
        caso = criar_caso()
        item = _criar_andamento(
            client, csrf_de(ADMIN), caso.id,
            descricao="Conteudo da movimentacao",
            ocorrido_em="2026-03-10T14:30:00",
        )
        resp = client.get(
            f"/api/casos/{caso.id}/andamentos/{item['id']}"
        )
        assert resp.status_code == 200, resp.text
        corpo = resp.json()
        assert corpo["titulo"] == "Andamento da Fase 6"
        assert corpo["descricao"] == "Conteudo da movimentacao"
        assert corpo["ocorrido_em"] == "2026-03-10T14:30:00"
        assert corpo["criado_por_nome"] == "Jadilson Silva"

    def test_detalhe_de_outro_caso_404(self, client, csrf_de, criar_caso):
        caso_a = criar_caso(cliente="Alvo A")
        caso_b = criar_caso(cliente="Alvo B")
        csrf = csrf_de(ADMIN)
        item_b = _criar_andamento(client, csrf, caso_b.id)
        # mesmo id, URL do caso A: nao pode vazar o vinculo
        resp = client.get(
            f"/api/casos/{caso_a.id}/andamentos/{item_b['id']}"
        )
        assert resp.status_code == 404, resp.text


# ------------------------------------------------- integridade historica


class TestIntegridadeHistorica:
    def test_nao_existem_rotas_de_edicao_ou_exclusao(
        self, client, csrf_de, criar_caso
    ):
        caso = criar_caso()
        csrf = csrf_de(ADMIN)
        item = _criar_andamento(client, csrf, caso.id)
        base = f"/api/casos/{caso.id}/andamentos/{item['id']}"
        for metodo in ("put", "patch", "delete"):
            resp = getattr(client, metodo)(base, headers={CSRF: csrf})
            assert resp.status_code in (404, 405), (
                f"{metodo.upper()} nao deveria existir no historico"
            )
        # a rota de lista tambem nao aceita exclusao em massa
        resp = client.delete(
            f"/api/casos/{caso.id}/andamentos", headers={CSRF: csrf}
        )
        assert resp.status_code in (404, 405)

        # o registro permanece intacto
        atual = client.get(base)
        assert atual.status_code == 200
        assert atual.json()["titulo"] == "Andamento da Fase 6"

    def test_correcao_por_registro_complementar(
        self, client, csrf_de, criar_caso
    ):
        caso = criar_caso()
        csrf = csrf_de(ADMIN)
        original = _criar_andamento(
            client, csrf, caso.id,
            titulo="Lancamento com erro",
            descricao="registro que precisa de retificacao",
        )
        # estrategia de retificacao: NOVO registro complementar - o original
        # nao e apagado nem sobrescrito.
        retificado = _criar_andamento(
            client, csrf, caso.id,
            titulo="Retificacao do lancamento anterior",
            descricao="correcao registrada como movimentacao nova",
            ocorrido_em="2026-03-11T10:00:00",
        )
        assert retificado["id"] != original["id"]

        corpo = client.get(f"/api/casos/{caso.id}/andamentos").json()
        assert corpo["total"] == 2

        busca = client.get(
            f"/api/casos/{caso.id}/andamentos/{original['id']}"
        ).json()
        assert busca["titulo"] == "Lancamento com erro"  # preservado

    def test_falha_no_registro_nada_persiste(
        self, client, csrf_de, criar_caso, db_session, monkeypatch
    ):
        from app.models.andamento import Andamento
        from app.repositories.andamento_repository import AndamentoRepository

        caso = criar_caso()
        monkeypatch.setattr(AndamentoRepository, "criar", _falha_apos_flush)
        with pytest.raises(RuntimeError, match="registro"):
            client.post(
                f"/api/casos/{caso.id}/andamentos",
                headers={CSRF: csrf_de(ADMIN)},
                json={"titulo": "Nao pode persistir"},
            )
        db_session.expire_all()
        persistido = (
            db_session.query(Andamento)
            .filter(Andamento.titulo == "Nao pode persistir")
            .count()
        )
        assert persistido == 0, "andamento persistido sem transacao integra"
