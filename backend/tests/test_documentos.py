"""Testes da Fase 3: documentos no banco, com escopo herdado do caso.

As mesmas regras de processos/andamentos valem aqui: fora do escopo e 404
(nunca 403, que revelaria existencia), e escrita exige permissao no caso.
"""

from tests.conftest import ADMIN, PADRAO

CSRF = "X-CSRF-Token"


def _doc(client, caso, cliente=None, headers=None, **extra):
    corpo = {
        "titulo": "Petição inicial – Maria",
        "area": "trabalhista",
        "tipo": "Reclamação trabalhista",
        "html": "<p>Inicial.</p>",
        "caso_id": caso.id,
    }
    if cliente is not None:
        corpo["cliente_id"] = cliente.id
    corpo.update(extra)
    return client.post("/api/documentos", headers=headers, json=corpo)


class TestDocumentosEscopo:
    def test_admin_cria_e_lista_documento_do_caso(
        self, client, csrf_admin, criar_caso, criar_cliente
    ):
        caso = criar_caso(cliente="Maria")
        cliente = criar_cliente("Maria")
        caso.cliente_id = cliente.id
        client_patch = client.patch(
            f"/api/casos/{caso.id}",
            headers={CSRF: csrf_admin},
            json={"cliente_id": cliente.id},
        )
        assert client_patch.status_code == 200

        resp = _doc(client, caso, cliente, headers={CSRF: csrf_admin})
        assert resp.status_code == 201, resp.text
        dados = resp.json()
        assert dados["caso_id"] == caso.id
        assert dados["cliente_id"] == cliente.id
        assert dados["criado_por"] is not None
        assert "atualizado_em" in dados

        lista = client.get("/api/documentos").json()
        assert [d["id"] for d in lista["itens"]] == [dados["id"]]
        assert lista["total"] == 1
        # O frontend carrega com limite=200; tem que ser aceito pela rota.
        assert client.get("/api/documentos?limite=200").status_code == 200

    def test_fora_do_escopo_404_na_lista_no_detalhe_e_na_criacao(
        self, client, csrf_de, admin, advogada, criar_caso, criar_cliente
    ):
        csrf_admin = csrf_de(ADMIN)
        caso = criar_caso(cliente="Maria")
        cliente = criar_cliente("Maria")
        resp = _doc(client, caso, cliente, headers={CSRF: csrf_admin})
        assert resp.status_code == 201
        documento_id = resp.json()["id"]

        csrf_de(PADRAO)  # troca o cookie da sessao para a advogada sem acesso
        assert client.get("/api/documentos").json()["itens"] == []
        assert client.get(f"/api/documentos/{documento_id}").status_code == 404
        # Mesmo com CSRF valido da advogada, o caso esta fora do escopo -> 404.
        assert _doc(client, caso, cliente, headers={CSRF: csrf_de(PADRAO)}).status_code == 404

    def test_com_concessao_le_200_mas_nao_escreve_sem_permissao(
        self, client, csrf_de, admin, advogada, criar_caso, conceder_acesso
    ):
        csrf_admin = csrf_de(ADMIN)
        caso = criar_caso(cliente="Maria")
        documento_id = _doc(client, caso, headers={CSRF: csrf_admin}).json()["id"]
        conceder_acesso(caso, advogada, pode_visualizar=True)

        csrf = csrf_de(PADRAO)
        assert client.get(f"/api/documentos/{documento_id}").status_code == 200
        edicao = client.patch(
            f"/api/documentos/{documento_id}",
            headers={CSRF: csrf},
            json={"html": "<p>Hackeado</p>"},
        )
        assert edicao.status_code == 403

    def test_concessao_de_processos_permite_escrever_e_mover(
        self,
        client,
        csrf_de,
        admin,
        advogada,
        criar_caso,
        criar_cliente,
        conceder_acesso,
    ):
        csrf_admin = csrf_de(ADMIN)
        caso = criar_caso(cliente="Maria")
        cliente = criar_cliente("Maria")
        caso.cliente_id = cliente.id
        documento_id = _doc(client, caso, headers={CSRF: csrf_admin}).json()["id"]
        conceder_acesso(
            caso, advogada, pode_visualizar=True, pode_gerenciar_processos=True
        )

        csrf = csrf_de(PADRAO)
        edicao = client.patch(
            f"/api/documentos/{documento_id}",
            headers={CSRF: csrf},
            json={"html": "<p>Atualizado pela colaboradora.</p>"},
        )
        assert edicao.status_code == 200, edicao.text
        assert "colaboradora" in edicao.json()["html"]

        anterior = client.get(f"/api/documentos/{documento_id}").json()
        movido = client.patch(
            f"/api/documentos/{documento_id}/mover",
            headers={CSRF: csrf},
            json={"cliente_id": cliente.id, "pasta_id": None},
        )
        assert movido.status_code == 200, movido.text
        assert movido.json()["cliente_id"] == cliente.id
        # Mover nao e edicao de conteudo: data de atualizacao preservada.
        assert movido.json()["atualizado_em"] == anterior["atualizado_em"]


class TestDocumentosAvulsos:
    def test_sem_caso_somente_admin_cria_ve_e_exclui(
        self, client, csrf_de, admin, advogada
    ):
        csrf_admin = csrf_de(ADMIN)
        resp = client.post(
            "/api/documentos",
            headers={CSRF: csrf_admin},
            json={"titulo": "Modelo interno", "html": "<p>Modelo.</p>"},
        )
        assert resp.status_code == 201
        documento_id = resp.json()["id"]
        assert resp.json()["caso_id"] is None

        csrf_de(PADRAO)
        assert client.get("/api/documentos").json()["itens"] == []
        assert client.get(f"/api/documentos/{documento_id}").status_code == 404
        negado = client.post(
            "/api/documentos",
            headers={CSRF: csrf_de(PADRAO)},
            json={"titulo": "Peca avulsa", "html": "<p>x</p>"},
        )
        assert negado.status_code == 403

        csrf_admin = csrf_de(ADMIN)
        assert (
            client.delete(
                f"/api/documentos/{documento_id}", headers={CSRF: csrf_admin}
            ).status_code
            == 204
        )
        assert client.get(f"/api/documentos/{documento_id}").status_code == 404


class TestDocumentosContrato:
    def test_payload_nao_pode_falsificar_id_ou_data(
        self, client, csrf_admin, criar_caso
    ):
        caso = criar_caso()
        resp = client.post(
            "/api/documentos",
            headers={CSRF: csrf_admin},
            json={
                "titulo": "Peca",
                "html": "<p>x</p>",
                "caso_id": caso.id,
                "id": 999,
                "atualizado_em": "2030-01-01T00:00:00",
            },
        )
        assert resp.status_code == 422

    def test_cliente_informado_deve_ser_o_cliente_do_caso(
        self, client, csrf_admin, criar_caso, criar_cliente
    ):
        caso = criar_caso(cliente="Maria")
        cliente = criar_cliente("Maria")
        caso.cliente_id = cliente.id
        outro = criar_cliente("Outro")
        resp = _doc(client, caso, outro, headers={CSRF: csrf_admin})
        assert resp.status_code == 422
        assert "cliente do caso" in resp.json()["detail"].lower()
