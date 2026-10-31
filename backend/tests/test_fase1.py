"""Testes da Fase 1: cadastro de usuarios, clientes e controle de acesso.

Todos os casos verificam respostas HTTP reais (status + corpo), cobrindo as
regras de autorizacao aplicadas NO SERVIDOR - esconder botao no frontend nao
conta como controle de acesso.
"""

from datetime import date, timedelta

from tests.conftest import ADMIN, FUNCIONARIO, PADRAO

CSRF = "X-CSRF-Token"

CPF_VALIDO = "123.456.789-09"
CNPJ_VALIDO = "11.222.333/0001-81"


def _ids(resp) -> set:
    return {item["id"] for item in resp.json()["itens"]}


# ------------------------------------------------------------- usuarios


class TestCadastroUsuarios:
    def test_cadastrar_usuario_como_admin_201_sem_privilegio(self, client, csrf_admin):
        resp = client.post(
            "/api/usuarios",
            headers={CSRF: csrf_admin},
            json={
                "nome": "Novo Funcionario",
                "email": "novo@jadilson.adv",
                "senha": "Novo@1234",
                "perfil": "FUNCIONARIO",
            },
        )
        assert resp.status_code == 201
        corpo = resp.json()
        assert corpo["perfil"] == "FUNCIONARIO"
        assert corpo["administrador"] is False
        assert corpo["ativo"] is True
        assert "senha_hash" not in resp.text

    def test_cadastro_nao_aceita_tornar_se_administrador_422(self, client, csrf_admin):
        """`administrador` nem e campo aceito: escalada de privilegio = 422."""
        resp = client.post(
            "/api/usuarios",
            headers={CSRF: csrf_admin},
            json={
                "nome": "Golpista",
                "email": "golpista@jadilson.adv",
                "senha": "Senha@123",
                "perfil": "ADVOGADO",
                "administrador": True,
            },
        )
        assert resp.status_code == 422
        assert client.get("/api/auth/me").status_code == 200  # sessao segue ok

    def test_cadastro_nao_aceita_perfil_ADMIN_legado_422(self, client, csrf_admin):
        """ADMIN deixou de existir como perfil: advogado principal = permissao."""
        resp = client.post(
            "/api/usuarios",
            headers={CSRF: csrf_admin},
            json={
                "nome": "Tentativa",
                "email": "tentativa@jadilson.adv",
                "senha": "Senha@123",
                "perfil": "ADMIN",
            },
        )
        assert resp.status_code == 422

    def test_admin_ativa_e_desativa_usuario(self, client, csrf_admin, advogada, fazer_login):
        usuarios = {u["email"]: u["id"] for u in client.get("/api/usuarios").json()}
        resp = client.patch(
            f"/api/usuarios/{usuarios[PADRAO['email']]}",
            headers={CSRF: csrf_admin},
            json={"ativo": False},
        )
        assert resp.status_code == 200
        assert resp.json()["ativo"] is False

        # conta desativada nao autentica mais (403) - RF02
        bloqueado = client.post(
            "/api/auth/login",
            json={"email": PADRAO["email"], "senha": PADRAO["senha"]},
        )
        assert bloqueado.status_code == 403
        assert "inativo" in bloqueado.json()["detail"].lower()

    def test_admin_troca_perfil_funcionario_para_advogado(self, client, csrf_admin, funcionario):
        resp = client.patch(
            f"/api/usuarios/{funcionario.id}",
            headers={CSRF: csrf_admin},
            json={"perfil": "ADVOGADO"},
        )
        assert resp.status_code == 200
        assert resp.json()["perfil"] == "ADVOGADO"
        assert resp.json()["administrador"] is False


class TestProtecaoDePrivilegios:
    def test_comum_nao_altera_proprio_perfil_403(self, client, csrf_de, advogada, db_session):
        csrf = csrf_de(PADRAO)
        resp = client.patch(
            f"/api/usuarios/{advogada.id}",
            headers={CSRF: csrf},
            json={"perfil": "FUNCIONARIO", "ativo": False},
        )
        assert resp.status_code == 403
        assert "advogado principal" in resp.json()["detail"].lower()
        db_session.refresh(advogada)
        assert advogada.perfil == "ADVOGADO" and advogada.ativo is True
        assert advogada.administrador is False

    def test_comum_nao_altera_outro_usuario_403(self, client, csrf_de, funcionario, advogada):
        csrf = csrf_de(PADRAO)
        resp = client.patch(
            f"/api/usuarios/{funcionario.id}",
            headers={CSRF: csrf},
            json={"ativo": False},
        )
        assert resp.status_code == 403

    def test_payload_de_administrador_e_rejeitado_mesmo_para_admin(
        self, client, csrf_admin, advogada, db_session
    ):
        resp = client.patch(
            f"/api/usuarios/{advogada.id}",
            headers={CSRF: csrf_admin},
            json={"administrador": True},
        )
        assert resp.status_code == 422
        db_session.refresh(advogada)
        assert advogada.administrador is False

    def test_administrao_consegue_verificacao_dequele_e_admin(self, client, csrf_admin, admin, advogada):
        """A permissao administrativa continua na conta provisionada."""
        usuarios = {u["email"]: u for u in client.get("/api/usuarios").json()}
        assert usuarios[ADMIN["email"]]["administrador"] is True
        assert usuarios[PADRAO["email"]]["administrador"] is False

    def test_usuario_inativo_nao_usa_endpoints_protegidos(self, client, csrf_de, advogada, db_session):
        csrf_de(PADRAO)  # sessao valida
        advogada.ativo = False
        db_session.commit()

        assert client.get("/api/auth/me").status_code == 401
        assert client.get("/api/casos").status_code == 401
        assert client.get("/api/clientes").status_code == 401
        assert client.get("/api/usuarios").status_code == 401

        # e o login volta a ser recusado (403, nao 401 - conta existe mas bloqueada)
        login = client.post(
            "/api/auth/login",
            json={"email": PADRAO["email"], "senha": PADRAO["senha"]},
        )
        assert login.status_code == 403

    def test_admin_inativo_tambem_perde_as_rotas_administrativas(
        self, client, csrf_de, admin, db_session
    ):
        csrf_de(ADMIN)
        admin.ativo = False
        db_session.commit()
        assert client.get("/api/usuarios").status_code == 401


# -------------------------------------------------------------- clientes


class TestCadastroClientes:
    def test_cadastrar_cliente_como_admin_201(self, client, csrf_admin):
        resp = client.post(
            "/api/clientes",
            headers={CSRF: csrf_admin},
            json={
                "nome": "  Maria da Silva  ",
                "cpf_cnpj": CPF_VALIDO,
                "email": "Maria@Exemplo.Com",
                "telefone": "(11) 99999-0000",
                "data_nascimento": "1990-05-20",
            },
        )
        assert resp.status_code == 201
        corpo = resp.json()
        assert corpo["nome"] == "Maria da Silva"
        assert corpo["cpf_cnpj"] == CPF_VALIDO  # formatado na saida
        assert corpo["email"] == "maria@exemplo.com"
        assert corpo["telefone"] == "11999990000"
        assert corpo["data_nascimento"] == "1990-05-20"
        assert "senha_hash" not in resp.text

    def test_cadastrar_cliente_pj_201(self, client, csrf_admin):
        resp = client.post(
            "/api/clientes",
            headers={CSRF: csrf_admin},
            json={"nome": "Empresa Exemplo Ltda.", "cpf_cnpj": CNPJ_VALIDO},
        )
        assert resp.status_code == 201
        assert resp.json()["cpf_cnpj"] == CNPJ_VALIDO

    def test_cpf_invalido_422(self, client, csrf_admin):
        resp = client.post(
            "/api/clientes",
            headers={CSRF: csrf_admin},
            json={"nome": "Cpf Ruim", "cpf_cnpj": "111.111.111-11"},
        )
        assert resp.status_code == 422
        assert "invalido" in resp.json()["detail"].lower()

    def test_cnpj_invalido_422(self, client, csrf_admin):
        resp = client.post(
            "/api/clientes",
            headers={CSRF: csrf_admin},
            json={"nome": "Cnpj Ruim", "cpf_cnpj": "11.222.333/0001-80"},
        )
        assert resp.status_code == 422

    def test_documento_com_quantidade_errada_422(self, client, csrf_admin):
        resp = client.post(
            "/api/clientes",
            headers={CSRF: csrf_admin},
            json={"nome": "Tamanho Ruim", "cpf_cnpj": "1234567890"},
        )
        assert resp.status_code == 422

    def test_documento_duplicado_409(self, client, csrf_admin):
        """Mesmo CPF com formatacao diferente nao vira outro cadastro."""
        primeiro = client.post(
            "/api/clientes",
            headers={CSRF: csrf_admin},
            json={"nome": "Primeira", "cpf_cnpj": CPF_VALIDO},
        )
        assert primeiro.status_code == 201
        segundo = client.post(
            "/api/clientes",
            headers={CSRF: csrf_admin},
            json={"nome": "Segunda", "cpf_cnpj": "12345678909"},
        )
        assert segundo.status_code == 409

    def test_documentos_ausentes_nao_colidem(self, client, csrf_admin):
        """Politica: sem documento = NULL, e o UNIQUE do banco ignora NULL."""
        um = client.post(
            "/api/clientes",
            headers={CSRF: csrf_admin},
            json={"nome": "Sem Doc Um", "cpf_cnpj": ""},
        )
        dois = client.post(
            "/api/clientes",
            headers={CSRF: csrf_admin},
            json={"nome": "Sem Doc Dois"},
        )
        assert um.status_code == 201 and dois.status_code == 201
        assert um.json()["cpf_cnpj"] is None and dois.json()["cpf_cnpj"] is None

    def test_telefone_invalido_422(self, client, csrf_admin):
        resp = client.post(
            "/api/clientes",
            headers={CSRF: csrf_admin},
            json={"nome": "Fone Ruim", "telefone": "ligue-me"},
        )
        assert resp.status_code == 422

    def test_data_nascimento_futura_422(self, client, csrf_admin):
        futura = (date.today() + timedelta(days=30)).isoformat()
        resp = client.post(
            "/api/clientes",
            headers={CSRF: csrf_admin},
            json={"nome": "Viajante do Tempo", "data_nascimento": futura},
        )
        assert resp.status_code == 422

    def test_comum_nao_cadastra_cliente_403(self, client, csrf_de, advogada):
        csrf = csrf_de(PADRAO)
        resp = client.post(
            "/api/clientes",
            headers={CSRF: csrf},
            json={"nome": "Intruso", "cpf_cnpj": CPF_VALIDO},
        )
        assert resp.status_code == 403

    def test_cliente_sem_sessao_401(self, client):
        assert client.get("/api/clientes").status_code == 401
        assert client.post("/api/clientes", json={"nome": "X"}).status_code == 401


class TestConsultaClientes:
    def test_admin_lista_todos_os_clientes(
        self, client, csrf_de, advogada, criar_caso, criar_cliente
    ):
        ligado = criar_cliente(nome="Ligada a Caso", cpf_cnpj="12345678909")
        solto = criar_cliente(nome="Sem Caso")
        criar_caso(cliente_id=ligado.id)  # caso sem concessao para ninguem

        csrf_de(ADMIN)
        resp = client.get("/api/clientes")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2
        assert resp.json()["itens"][0]["cpf_cnpj"] == CPF_VALIDO

    def test_colaborador_consulta_cliente_do_caso_autorizado(
        self, client, csrf_de, advogada, criar_caso, criar_cliente
    ):
        cliente = criar_cliente(nome="Paula Cadastrada", cpf_cnpj="12345678909")
        caso = criar_caso(cliente="Paula Cadastrada", cliente_id=cliente.id)

        csrf = csrf_de(ADMIN)
        concedeu = client.post(
            f"/api/casos/{caso.id}/usuarios",
            headers={CSRF: csrf},
            json={"usuario_id": advogada.id},
        )
        assert concedeu.status_code == 201

        csrf_de(PADRAO)
        lista = client.get("/api/clientes")
        assert lista.status_code == 200
        assert [c["nome"] for c in lista.json()["itens"]] == ["Paula Cadastrada"]
        assert client.get(f"/api/clientes/{cliente.id}").status_code == 200

    def test_funcionario_consulta_cliente_do_caso_autorizado(
        self, client, csrf_de, funcionario, criar_caso, criar_cliente
    ):
        cliente = criar_cliente(nome="Rafael Contratante")
        caso = criar_caso(cliente_id=cliente.id)
        criar_caso()  # outro caso, sem vinculo e sem concessao

        csrf = csrf_de(ADMIN)
        assert (
            client.post(
                f"/api/casos/{caso.id}/usuarios",
                headers={CSRF: csrf},
                json={"usuario_id": funcionario.id},
            ).status_code
            == 201
        )

        csrf_de(FUNCIONARIO)
        lista = client.get("/api/clientes")
        assert lista.status_code == 200
        assert [c["nome"] for c in lista.json()["itens"]] == ["Rafael Contratante"]

    def test_consulta_nao_autorizada_e_bloqueada(
        self, client, csrf_de, advogada, criar_caso, criar_cliente
    ):
        cliente = criar_cliente(nome="Invisivel")
        criar_caso(cliente_id=cliente.id)

        csrf_de(PADRAO)
        lista = client.get("/api/clientes")
        assert lista.status_code == 200
        assert lista.json() == {"itens": [], "total": 0, "pagina": 1, "limite": 20}
        # detalhe responde 404 (nao 403) para nao confirmar que o cadastro existe
        assert client.get(f"/api/clientes/{cliente.id}").status_code == 404

    def test_cliente_inexistente_404_para_admin(self, client, csrf_de):
        csrf_de(ADMIN)
        assert client.get("/api/clientes/9999").status_code == 404


# --------------------------------------------- controle de acesso a casos


class TestAcessoACasos:
    def test_admin_acessa_todos_os_casos(self, client, csrf_de, advogada, criar_caso):
        caso_a = criar_caso(cliente="A")
        caso_b = criar_caso(cliente="B")

        csrf = csrf_de(ADMIN)
        assert (
            client.post(
                f"/api/casos/{caso_a.id}/usuarios",
                headers={CSRF: csrf},
                json={"usuario_id": advogada.id},
            ).status_code
            == 201
        )

        resp = client.get("/api/casos")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2
        assert _ids(resp) == {caso_a.id, caso_b.id}
        assert client.get(f"/api/casos/{caso_b.id}").status_code == 200

    def test_colaborador_ve_somente_casos_autorizados(
        self, client, csrf_de, advogada, criar_caso
    ):
        caso_a = criar_caso(cliente="Autorizado")
        caso_b = criar_caso(cliente="De Outro Advogado")

        csrf = csrf_de(ADMIN)
        assert (
            client.post(
                f"/api/casos/{caso_a.id}/usuarios",
                headers={CSRF: csrf},
                json={"usuario_id": advogada.id},
            ).status_code
            == 201
        )

        csrf_de(PADRAO)
        lista = client.get("/api/casos")
        assert lista.status_code == 200
        assert lista.json()["total"] == 1
        assert _ids(lista) == {caso_a.id}
        assert client.get(f"/api/casos/{caso_a.id}").status_code == 200
        # trocar o id da URL nao concede acesso: 404 (nao 403, nao vaza existencia)
        assert client.get(f"/api/casos/{caso_b.id}").status_code == 404

    def test_funcionario_ve_somente_casos_autorizados(
        self, client, csrf_de, funcionario, criar_caso
    ):
        caso_a = criar_caso(cliente="Do Funcionario")
        caso_b = criar_caso(cliente="Nao Autorizado")

        csrf = csrf_de(ADMIN)
        assert (
            client.post(
                f"/api/casos/{caso_a.id}/usuarios",
                headers={CSRF: csrf},
                json={"usuario_id": funcionario.id},
            ).status_code
            == 201
        )

        csrf_de(FUNCIONARIO)
        lista = client.get("/api/casos")
        assert _ids(lista) == {caso_a.id}
        assert client.get(f"/api/casos/{caso_b.id}").status_code == 404

    def test_usuario_sem_associacao_nao_acessa_o_caso(
        self, client, csrf_de, advogada, criar_caso
    ):
        caso = criar_caso()
        csrf_de(PADRAO)
        assert client.get(f"/api/casos/{caso.id}").status_code == 404
        assert client.get("/api/casos").json()["total"] == 0

    def test_casos_sem_sessao_401(self, client, criar_caso):
        caso = criar_caso()
        assert client.get("/api/casos").status_code == 401
        assert client.get(f"/api/casos/{caso.id}").status_code == 401

    def test_prazos_respeitam_o_mesmo_escopo(
        self, client, csrf_de, advogada, criar_caso, db_session
    ):
        from app.models.prazo import Prazo

        caso = criar_caso()
        db_session.add(
            Prazo(
                caso_id=caso.id,
                titulo="Prazo de outro advogado",
                data_limite=date.today() + timedelta(days=2),
            )
        )
        db_session.commit()

        csrf_de(PADRAO)
        assert client.get("/api/prazos/urgentes").json()["total"] == 0

        csrf = csrf_de(ADMIN)
        assert (
            client.post(
                f"/api/casos/{caso.id}/usuarios",
                headers={CSRF: csrf},
                json={"usuario_id": advogada.id},
            ).status_code
            == 201
        )

        csrf_de(PADRAO)
        resp = client.get("/api/prazos/urgentes")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


class TestGestaoDePermissoes:
    def test_comum_nao_concede_acesso_403(self, client, csrf_de, advogada, funcionario, criar_caso):
        caso = criar_caso()
        csrf = csrf_de(PADRAO)
        resp = client.post(
            f"/api/casos/{caso.id}/usuarios",
            headers={CSRF: csrf},
            json={"usuario_id": funcionario.id},
        )
        assert resp.status_code == 403
        assert "advogado principal" in resp.json()["detail"].lower()

    def test_comum_nao_revoga_acesso_403(
        self, client, csrf_de, advogada, funcionario, criar_caso, conceder_acesso
    ):
        caso = criar_caso()
        conceder_acesso(caso, advogada)

        csrf = csrf_de(PADRAO)
        resp = client.delete(
            f"/api/casos/{caso.id}/usuarios/{advogada.id}", headers={CSRF: csrf}
        )
        assert resp.status_code == 403

    def test_comum_nao_lista_usuarios_do_caso_403(self, client, csrf_de, advogada, criar_caso):
        caso = criar_caso()
        csrf = csrf_de(PADRAO)
        assert client.get(f"/api/casos/{caso.id}/usuarios", headers={CSRF: csrf}).status_code == 403

    def test_concede_sem_token_csrf_403(self, client, csrf_admin, advogada, criar_caso):
        caso = criar_caso()
        resp = client.post(
            f"/api/casos/{caso.id}/usuarios", json={"usuario_id": advogada.id}
        )  # cookie valido, header ausente
        assert resp.status_code == 403
        assert "csrf" in resp.json()["detail"].lower()

    def test_associacao_duplicada_409(self, client, csrf_de, advogada, criar_caso):
        caso = criar_caso()
        csrf = csrf_de(ADMIN)
        payload = {"usuario_id": advogada.id}
        assert client.post(f"/api/casos/{caso.id}/usuarios", headers={CSRF: csrf}, json=payload).status_code == 201
        repetida = client.post(f"/api/casos/{caso.id}/usuarios", headers={CSRF: csrf}, json=payload)
        assert repetida.status_code == 409
        assert len(client.get(f"/api/casos/{caso.id}/usuarios").json()) == 1

    def test_concessao_a_si_mesmo_403(self, client, csrf_de, admin, criar_caso):
        caso = criar_caso()
        csrf = csrf_de(ADMIN)
        resp = client.post(
            f"/api/casos/{caso.id}/usuarios",
            headers={CSRF: csrf},
            json={"usuario_id": admin.id},
        )
        assert resp.status_code == 403

    def test_concessao_para_usuario_inexistente_404(self, client, csrf_de, criar_caso):
        caso = criar_caso()
        csrf = csrf_de(ADMIN)
        resp = client.post(
            f"/api/casos/{caso.id}/usuarios",
            headers={CSRF: csrf},
            json={"usuario_id": 99999},
        )
        assert resp.status_code == 404

    def test_concessao_para_caso_inexistente_404(self, client, csrf_de, advogada):
        csrf = csrf_de(ADMIN)
        resp = client.post(
            "/api/casos/99999/usuarios",
            headers={CSRF: csrf},
            json={"usuario_id": advogada.id},
        )
        assert resp.status_code == 404

    def test_concessao_para_usuario_inativo_422(self, client, csrf_de, advogada, criar_caso):
        advogada.ativo = False
        caso = criar_caso()
        csrf = csrf_de(ADMIN)
        resp = client.post(
            f"/api/casos/{caso.id}/usuarios",
            headers={CSRF: csrf},
            json={"usuario_id": advogada.id},
        )
        assert resp.status_code == 422

    def test_concessao_sem_visualizacao_422(self, client, csrf_de, advogada, criar_caso):
        caso = criar_caso()
        csrf = csrf_de(ADMIN)
        resp = client.post(
            f"/api/casos/{caso.id}/usuarios",
            headers={CSRF: csrf},
            json={"usuario_id": advogada.id, "pode_visualizar": False},
        )
        assert resp.status_code == 422

    def test_revogacao_204_perda_de_acesso_e_historico(
        self, client, csrf_de, admin, advogada, criar_caso
    ):
        caso = criar_caso()
        csrf = csrf_de(ADMIN)
        assert (
            client.post(
                f"/api/casos/{caso.id}/usuarios",
                headers={CSRF: csrf},
                json={"usuario_id": advogada.id},
            ).status_code
            == 201
        )
        csrf_de(PADRAO)
        assert client.get(f"/api/casos/{caso.id}").status_code == 200

        csrf = csrf_de(ADMIN)
        revogou = client.delete(
            f"/api/casos/{caso.id}/usuarios/{advogada.id}", headers={CSRF: csrf}
        )
        assert revogou.status_code == 204
        # revogar de novo nao existe (404)
        assert (
            client.delete(
                f"/api/casos/{caso.id}/usuarios/{advogada.id}", headers={CSRF: csrf}
            ).status_code
            == 404
        )

        csrf_de(PADRAO)
        assert client.get(f"/api/casos/{caso.id}").status_code == 404
        assert client.get("/api/casos").json()["total"] == 0

        # rastreabilidade: a linha continua la, marcada como revogada
        csrf = csrf_de(ADMIN)
        ativos = client.get(f"/api/casos/{caso.id}/usuarios").json()
        historico = client.get(
            f"/api/casos/{caso.id}/usuarios?incluir_revogados=true"
        ).json()
        assert ativos == []
        assert len(historico) == 1
        assert historico[0]["ativo"] is False
        assert historico[0]["concedido_por"] == admin.id
        assert historico[0]["revogado_por"] == admin.id
        assert historico[0]["revogado_em"] is not None

    def test_reconceder_apos_revogacao_reativa_sem_duplicar(
        self, client, csrf_de, advogada, criar_caso
    ):
        caso = criar_caso()
        csrf = csrf_de(ADMIN)
        payload = {"usuario_id": advogada.id}
        assert client.post(f"/api/casos/{caso.id}/usuarios", headers={CSRF: csrf}, json=payload).status_code == 201
        assert client.delete(f"/api/casos/{caso.id}/usuarios/{advogada.id}", headers={CSRF: csrf}).status_code == 204
        assert client.post(f"/api/casos/{caso.id}/usuarios", headers={CSRF: csrf}, json=payload).status_code == 201

        assert len(client.get(f"/api/casos/{caso.id}/usuarios").json()) == 1
        # o historico antigo nao vira uma segunda linha
        assert len(client.get(f"/api/casos/{caso.id}/usuarios?incluir_revogados=true").json()) == 1

        csrf_de(PADRAO)
        assert client.get(f"/api/casos/{caso.id}").status_code == 200

    def test_admin_lista_usuarios_associados_ao_caso(
        self, client, csrf_de, advogada, criar_caso
    ):
        caso = criar_caso()
        csrf = csrf_de(ADMIN)
        client.post(
            f"/api/casos/{caso.id}/usuarios",
            headers={CSRF: csrf},
            json={"usuario_id": advogada.id, "pode_gerenciar_prazos": True},
        )
        resp = client.get(f"/api/casos/{caso.id}/usuarios")
        assert resp.status_code == 200
        assert [u["usuario"]["email"] for u in resp.json()] == [PADRAO["email"]]
        assert resp.json()[0]["pode_gerenciar_prazos"] is True
        assert "senha_hash" not in resp.text

    def test_administrao_nao_pode_conceder_ao_funcionario_sem_caso(
        self, client, csrf_de, advogada, funcionario, criar_caso
    ):
        """Cobertura do bloqueio de quem nao tem nenhum caso (sem associaçao)."""
        caso = criar_caso()
        csrf = csrf_de(PADRAO)
        resp = client.post(
            f"/api/casos/{caso.id}/usuarios",
            headers={CSRF: csrf},
            json={"usuario_id": funcionario.id},
        )
        assert resp.status_code == 403
