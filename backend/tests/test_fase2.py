"""Testes da Fase 2: gerenciamento de casos juridicos.

Todos os casos verificam respostas HTTP reais (status + corpo), cobrindo as
regras de negocio E de autorizacao aplicadas no servidor. A Fase 1 continua
coberta por test_fase1.py (executada junto na suíte).
"""

from datetime import date, timedelta

from tests.conftest import ADMIN, FUNCIONARIO, PADRAO

CSRF = "X-CSRF-Token"


def _ids(resp) -> set:
    return {item["id"] for item in resp.json()["itens"]}


def _criar_caso_api(client, csrf, **dados):
    """Cria um caso pela API e devolve o corpo (201)."""
    payload = {
        "titulo": "Acao de cobranca bancaria",
        "cliente_id": dados.pop("cliente_id"),
    }
    payload.update(dados)
    resp = client.post("/api/casos", headers={CSRF: csrf}, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# --------------------------------------------------------------- cadastro


class TestCriacaoCasos:
    def test_caso_valido_201_sem_numero_de_processo(self, client, csrf_de, criar_cliente):
        """Um caso administrativo NAO tem numero de processo - e isso e valido."""
        cliente = criar_cliente(nome="Maria da Silva")
        resp = client.post(
            "/api/casos",
            headers={CSRF: csrf_de(ADMIN)},
            json={
                "titulo": "Recurso administrativo INSS",
                "cliente_id": cliente.id,
                "tipo_demanda": "ADMINISTRATIVA",
                "area": "PREVIDENCIARIO",
                "prioridade": "ALTA",
            },
        )
        assert resp.status_code == 201, resp.text
        corpo = resp.json()
        assert corpo["titulo"] == "Recurso administrativo INSS"
        assert corpo["numero_processo"] is None
        assert corpo["cliente_id"] == cliente.id
        assert corpo["tipo_demanda"] == "ADMINISTRATIVA"
        assert corpo["prioridade"] == "ALTA"
        assert corpo["status"] == "NOVO"
        assert corpo["data_abertura"] == date.today().isoformat()  # padrao: hoje
        assert corpo["arquivado"] is False
        assert corpo["criado_por"] is not None  # operador registrado
        assert "senha_hash" not in resp.text

    def test_dois_casos_sem_processo_nao_colidem(self, client, csrf_de, criar_cliente):
        """O UNIQUE de numero_processo ignora NULL: sem processo nao ha conflito."""
        cliente = criar_cliente(nome="Empresa X")
        csrf = csrf_de(ADMIN)
        primeiro = _criar_caso_api(
            client, csrf, cliente_id=cliente.id, titulo="Adm um"
        )
        segundo = _criar_caso_api(
            client, csrf, cliente_id=cliente.id, titulo="Adm dois"
        )
        assert primeiro["id"] != segundo["id"]

    def test_caso_com_processo_e_completo(self, client, csrf_de, criar_cliente, advogada):
        cliente = criar_cliente(nome="Rafael Almeida")
        resp = client.post(
            "/api/casos",
            headers={CSRF: csrf_de(ADMIN)},
            json={
                "titulo": "Execucao bancaria",
                "cliente_id": cliente.id,
                "numero_processo": "0001111-22.2026.8.26.0100",
                "area": "BANCARIO",
                "tipo_demanda": "JUDICIAL",
                "status": "EM_ANDAMENTO",
                "prioridade": "URGENTE",
                "data_abertura": "2026-01-15",
                "responsavel_id": advogada.id,
                "parte_contraria": "Banco Aurora",
                "tribunal": "TJSP",
                "vara": "1a Vara Civel",
                "descricao": "Cobranca indevida de tarifas",
                "observacoes": "Cliente com defesa tecnica",
            },
        )
        assert resp.status_code == 201, resp.text
        corpo = resp.json()
        assert corpo["numero_processo"] == "0001111-22.2026.8.26.0100"
        assert corpo["data_abertura"] == "2026-01-15"
        assert corpo["responsavel_id"] == advogada.id
        assert corpo["responsavel_nome"] == PADRAO["nome"]
        assert corpo["parte_contraria"] == "Banco Aurora"

    def test_caso_judicial_sem_numero_e_valido(self, client, csrf_de, criar_cliente):
        """Nem todo caso judicial tem numero ainda (distribuicao pendente)."""
        cliente = criar_cliente(nome="Sem Numero")
        resp = client.post(
            "/api/casos",
            headers={CSRF: csrf_de(ADMIN)},
            json={"titulo": "Aguardando distribuicao", "cliente_id": cliente.id},
        )
        assert resp.status_code == 201
        assert resp.json()["numero_processo"] is None

    def test_sem_cliente_422(self, client, csrf_de):
        resp = client.post(
            "/api/casos",
            headers={CSRF: csrf_de(ADMIN)},
            json={"titulo": "Caso sem cliente"},
        )
        assert resp.status_code == 422  # cliente_id e obrigatorio

    def test_titulo_curto_422(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="X")
        resp = client.post(
            "/api/casos",
            headers={CSRF: csrf_de(ADMIN)},
            json={"titulo": "ab", "cliente_id": cliente.id},
        )
        assert resp.status_code == 422

    def test_cliente_inexistente_404(self, client, csrf_de):
        resp = client.post(
            "/api/casos",
            headers={CSRF: csrf_de(ADMIN)},
            json={"titulo": "Cliente fantasma", "cliente_id": 99999},
        )
        assert resp.status_code == 404

    def test_cliente_sem_acesso_404_para_comum(self, client, csrf_de, advogada, criar_cliente):
        """Advogado comum nao cria caso com cliente que nao e seu (404, sem vazar)."""
        cliente = criar_cliente(nome="De Outro Advogado")
        resp = client.post(
            "/api/casos",
            headers={CSRF: csrf_de(PADRAO)},
            json={"titulo": "Invasao de escopo", "cliente_id": cliente.id},
        )
        assert resp.status_code == 404

    def test_cliente_inativo_422(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Inativo", ativo=False)
        resp = client.post(
            "/api/casos",
            headers={CSRF: csrf_de(ADMIN)},
            json={"titulo": "Cliente desativado", "cliente_id": cliente.id},
        )
        assert resp.status_code == 422

    def test_funcionario_nao_cria_caso_403(self, client, csrf_de, funcionario, criar_cliente):
        cliente = criar_cliente(nome="Qualquer")
        resp = client.post(
            "/api/casos",
            headers={CSRF: csrf_de(FUNCIONARIO)},
            json={"titulo": "Funcionario tenta criar", "cliente_id": cliente.id},
        )
        assert resp.status_code == 403
        assert "advogado" in resp.json()["detail"].lower()

    def test_sem_sessao_401(self, client, criar_cliente):
        cliente = criar_cliente(nome="Publico")
        assert (
            client.post(
                "/api/casos", json={"titulo": "Sem sessao", "cliente_id": cliente.id}
            ).status_code
            == 401
        )

    def test_sem_csrf_403(self, client, csrf_admin, criar_cliente):
        cliente = criar_cliente(nome="CSRF")
        resp = client.post(
            "/api/casos", json={"titulo": "Sem token", "cliente_id": cliente.id}
        )  # cookie valido, header ausente
        assert resp.status_code == 403
        assert "csrf" in resp.json()["detail"].lower()

    def test_responsavel_inexistente_422(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Resp")
        resp = client.post(
            "/api/casos",
            headers={CSRF: csrf_de(ADMIN)},
            json={
                "titulo": "Responsavel fantasma",
                "cliente_id": cliente.id,
                "responsavel_id": 99999,
            },
        )
        assert resp.status_code == 422

    def test_responsavel_inativo_422(self, client, csrf_de, criar_cliente, advogada):
        advogada.ativo = False
        cliente = criar_cliente(nome="Resp Inativo")
        resp = client.post(
            "/api/casos",
            headers={CSRF: csrf_de(ADMIN)},
            json={
                "titulo": "Responsavel bloqueado",
                "cliente_id": cliente.id,
                "responsavel_id": advogada.id,
            },
        )
        assert resp.status_code == 422
        assert "ativo" in resp.json()["detail"].lower()

    def test_responsavel_funcionario_422(self, client, csrf_de, criar_cliente, funcionario):
        cliente = criar_cliente(nome="Resp Func")
        resp = client.post(
            "/api/casos",
            headers={CSRF: csrf_de(ADMIN)},
            json={
                "titulo": "Responsavel nao e advogado",
                "cliente_id": cliente.id,
                "responsavel_id": funcionario.id,
            },
        )
        assert resp.status_code == 422
        assert "advogado" in resp.json()["detail"].lower()

    def test_comum_nao_attribui_terceiro_como_responsavel_403(
        self, client, csrf_de, advogada, criar_cliente, criar_caso, conceder_acesso
    ):
        """So o admin atribui o caso a outro advogado."""
        cliente = criar_cliente(nome="Escopo")
        # cliente acessivel a advogada (atraves de um caso ja autorizado)
        caso_base = criar_caso(cliente_id=cliente.id)
        conceder_acesso(caso_base, advogada)

        resp = client.post(
            "/api/casos",
            headers={CSRF: csrf_de(PADRAO)},
            json={
                "titulo": "Quero indicar outro",
                "cliente_id": cliente.id,
                "responsavel_id": 1,  # admin
            },
        )
        assert resp.status_code == 403

    def test_criacao_registra_acesso_automatico_para_responsavel(
        self, client, csrf_de, advogada, criar_cliente
    ):
        """O responsavel precisa enxergar o caso que e dele."""
        cliente = criar_cliente(nome="Auto acesso")
        _criar_caso_api(
            client,
            csrf_de(ADMIN),
            cliente_id=cliente.id,
            titulo="Caso da Ana",
            responsavel_id=advogada.id,
        )
        # advogada (comum) enxerga o caso sem concessao manual
        casos = client.get("/api/casos", headers={CSRF: csrf_de(PADRAO)})
        assert casos.status_code == 200
        assert any(c["titulo"] == "Caso da Ana" for c in casos.json()["itens"])

    def test_numero_processo_duplicado_409(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Dup")
        csrf = csrf_de(ADMIN)
        _criar_caso_api(
            client,
            csrf,
            cliente_id=cliente.id,
            numero_processo="0009999-99.2026.8.26.0100",
        )
        repetido = client.post(
            "/api/casos",
            headers={CSRF: csrf},
            json={
                "titulo": "Duplicado",
                "cliente_id": cliente.id,
                "numero_processo": "0009999-99.2026.8.26.0100",
            },
        )
        assert repetido.status_code == 409

    def test_campos_administrativos_sao_rejeitados_422(self, client, csrf_de, criar_cliente):
        """Nao ha escalada: arquivado/criado_por nao sao aceitos no payload."""
        cliente = criar_cliente(nome="Golpe")
        resp = client.post(
            "/api/casos",
            headers={CSRF: csrf_de(ADMIN)},
            json={
                "titulo": "Tentativa de escalada",
                "cliente_id": cliente.id,
                "arquivado": True,
                "criado_por": 999,
            },
        )
        assert resp.status_code == 422


# --------------------------------------------------------------- listagem


class TestListagemCasos:
    def test_paginacao_no_banco(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Pagina")
        csrf = csrf_de(ADMIN)
        for n in range(3):
            _criar_caso_api(client, csrf, cliente_id=cliente.id, titulo=f"Caso {n}")

        primeira = client.get("/api/casos?limite=2&pagina=1")
        assert primeira.status_code == 200
        assert primeira.json()["total"] == 3
        assert len(primeira.json()["itens"]) == 2
        segunda = client.get("/api/casos?limite=2&pagina=2")
        assert len(segunda.json()["itens"]) == 1

    def test_filtros(self, client, csrf_de, criar_cliente, advogada, funcionario):
        cliente = criar_cliente(nome="Filtros")
        csrf = csrf_de(ADMIN)
        alvo = _criar_caso_api(
            client,
            csrf,
            cliente_id=cliente.id,
            titulo="Filtro completo",
            area="CONSUMIDOR",
            tipo_demanda="EXTRAJUDICIAL",
            status="AGUARDANDO_CLIENTE",
            prioridade="URGENTE",
            responsavel_id=advogada.id,
        )
        _criar_caso_api(
            client,
            csrf,
            cliente_id=cliente.id,
            titulo="Outro caso",
            area="BANCARIO",
            tipo_demanda="JUDICIAL",
        )

        def ids_da_url(query: str) -> set:
            resp = client.get(f"/api/casos?{query}")
            assert resp.status_code == 200, resp.text
            return _ids(resp)

        assert len(ids_da_url("limite=100")) == 2  # sanidade: admin ve os dois
        assert ids_da_url(f"area=CONSUMIDOR&limite=100") == {alvo["id"]}
        assert ids_da_url("tipo_demanda=EXTRAJUDICIAL&limite=100") == {alvo["id"]}
        assert ids_da_url("status=AGUARDANDO_CLIENTE&limite=100") == {alvo["id"]}
        assert ids_da_url("prioridade=URGENTE&limite=100") == {alvo["id"]}
        assert ids_da_url(f"responsavel_id={advogada.id}&limite=100") == {alvo["id"]}
        assert ids_da_url(f"cliente_id={cliente.id}&limite=100") == {alvo["id"]} | {
            i for i in ids_da_url("limite=100") if i != alvo["id"]
        }  # os dois casos sao do mesmo cliente
        assert ids_da_url("q=Filtro completo&limite=100") == {alvo["id"]}

    def test_ordenacao_por_prioridade(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Ordena")
        csrf = csrf_de(ADMIN)
        _criar_caso_api(client, csrf, cliente_id=cliente.id, titulo="Baixa", prioridade="BAIXA")
        urgente = _criar_caso_api(
            client, csrf, cliente_id=cliente.id, titulo="Urgente", prioridade="URGENTE"
        )
        _criar_caso_api(client, csrf, cliente_id=cliente.id, titulo="Alta", prioridade="ALTA")

        resp = client.get("/api/casos?ordenar=prioridade&limite=100")
        assert resp.status_code == 200
        assert resp.json()["itens"][0]["id"] == urgente["id"]

    def test_ordenacao_por_abertura(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Abertura")
        csrf = csrf_de(ADMIN)
        antigo = _criar_caso_api(
            client, csrf, cliente_id=cliente.id, titulo="Antigo", data_abertura="2024-01-01"
        )
        _criar_caso_api(
            client, csrf, cliente_id=cliente.id, titulo="Novo", data_abertura="2026-06-01"
        )
        resp = client.get("/api/casos?limite=100")
        assert resp.json()["itens"][0]["id"] != antigo["id"]  # mais recente primeiro

    def test_ordenar_invalido_422(self, client, csrf_de):
        csrf_de(ADMIN)  # valida a sessao antes da consulta
        resp = client.get("/api/casos?ordenar=inexistente")
        assert resp.status_code == 422

    def test_filtros_nao_vazam_casos_alheios(
        self, client, csrf_de, advogada, criar_cliente, criar_caso, conceder_acesso
    ):
        """Filtro e paginacao nunca burlam o escopo da Fase 1."""
        cliente_visivel = criar_cliente(nome="Minha")
        cliente_alheio = criar_cliente(nome="Alheio")
        meu = criar_caso(cliente_id=cliente_visivel.id)
        alheio = criar_caso(cliente_id=cliente_alheio.id, area="BANCARIO")
        conceder_acesso(meu, advogada)

        csrf = csrf_de(PADRAO)
        normal = client.get("/api/casos?limite=100")
        assert _ids(normal) == {meu.id}

        # tentativas de contorno: filtro por area do caso alheio, busca e pagina
        por_area = client.get("/api/casos?area=BANCARIO&limite=100")
        assert por_area.json()["total"] == 0
        por_busca = client.get("/api/casos?q=Alheio&limite=100")
        assert por_busca.json()["total"] == 0
        por_cliente = client.get(f"/api/casos?cliente_id={cliente_alheio.id}")
        assert por_cliente.json()["total"] == 0
        assert alheio.id not in _ids(normal)

    def test_detalhe_caso_nao_autorizado_404(self, client, csrf_de, advogada, criar_caso):
        caso = criar_caso()
        resp = client.get(f"/api/casos/{caso.id}", headers={CSRF: csrf_de(PADRAO)})
        assert resp.status_code == 404  # mesmo codigo do caso inexistente
        assert client.get("/api/casos/99999").status_code == 404

    def test_caso_legado_sem_titulo_continua_legivel(
        self, client, csrf_de, db_session
    ):
        """Casos criados antes da Fase 2 (sem titulo) seguem respondendo."""
        from app.models.caso import Caso

        caso = Caso(cliente="Legado", numero_processo="1", area="Civel")
        db_session.add(caso)
        db_session.commit()
        csrf_de(ADMIN)
        resp = client.get(f"/api/casos/{caso.id}")
        assert resp.status_code == 200
        assert resp.json()["titulo"] is None
        assert resp.json()["numero_processo"] == "1"


# ------------------------------------------------------------- atualizacao


class TestAtualizacaoCasos:
    def test_admin_atualiza_qualquer_caso(self, client, csrf_de, advogada, criar_caso):
        caso = criar_caso()
        resp = client.patch(
            f"/api/casos/{caso.id}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"titulo": "Titulo revisado", "prioridade": "URGENTE"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["titulo"] == "Titulo revisado"
        assert resp.json()["prioridade"] == "URGENTE"

    def test_responsavel_atualiza_o_proprio_caso(
        self, client, csrf_de, advogada, criar_cliente
    ):
        cliente = criar_cliente(nome="Resp edita")
        caso = _criar_caso_api(
            client,
            csrf_de(ADMIN),
            cliente_id=cliente.id,
            titulo="Da Ana",
            responsavel_id=advogada.id,
        )
        resp = client.patch(
            f"/api/casos/{caso['id']}",
            headers={CSRF: csrf_de(PADRAO)},
            json={"status": "AGUARDANDO_SENTENCA", "observacoes": "Revisado pela Ana"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "AGUARDANDO_SENTENCA"

    def test_como_responsavel_pode_trocar_o_proprio_status_para_funcionario(
        self, client, csrf_de, advogada, criar_cliente
    ):
        """Sanidade do gate: responsavel e advogado - passa por require_advogado."""
        cliente = criar_cliente(nome="Gate")
        caso = _criar_caso_api(
            client, csrf_de(ADMIN), cliente_id=cliente.id, responsavel_id=advogada.id
        )
        resp = client.patch(
            f"/api/casos/{caso['id']}",
            headers={CSRF: csrf_de(PADRAO)},
            json={"status": "SUSPENSO"},
        )
        assert resp.status_code == 200

    def test_funcionario_com_acesso_nao_atualiza_403(
        self, client, csrf_de, funcionario, criar_caso, conceder_acesso
    ):
        """Mesmo com acesso ao caso, funcionario nao tem edicao."""
        caso = criar_caso()
        conceder_acesso(caso, funcionario)
        resp = client.patch(
            f"/api/casos/{caso.id}",
            headers={CSRF: csrf_de(FUNCIONARIO)},
            json={"titulo": "Funcionario edita"},
        )
        assert resp.status_code == 403

    def test_advogado_com_acesso_mas_nao_responsavel_403(
        self, client, csrf_de, advogada, criar_caso, conceder_acesso
    ):
        """Acesso de visualizacao nao e permissao de edicao."""
        caso = criar_caso()
        conceder_acesso(caso, advogada)  # so pode_visualizar
        resp = client.patch(
            f"/api/casos/{caso.id}",
            headers={CSRF: csrf_de(PADRAO)},
            json={"titulo": "Nao sou responsavel"},
        )
        assert resp.status_code == 403
        assert "responsavel" in resp.json()["detail"].lower()

    def test_caso_nao_autorizado_404(self, client, csrf_de, advogada, criar_caso):
        caso = criar_caso()
        resp = client.patch(
            f"/api/casos/{caso.id}",
            headers={CSRF: csrf_de(PADRAO)},
            json={"titulo": "Fora do escopo"},
        )
        assert resp.status_code == 404  # nao revela que o caso existe

    def test_escalada_de_privilegio_422(self, client, csrf_de, advogada, criar_caso):
        """Payload com campos administrativos e recusado (extra=forbid)."""
        caso = criar_caso()
        resp = client.patch(
            f"/api/casos/{caso.id}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"arquivado": True, "criado_por": 999},
        )
        assert resp.status_code == 422

    def test_responsavel_nao_muda_para_inativo_422(
        self, client, csrf_de, advogada, criar_cliente
    ):
        cliente = criar_cliente(nome="Troca resp")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente_id=cliente.id)
        advogada.ativo = False
        resp = client.patch(
            f"/api/casos/{caso['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"responsavel_id": advogada.id},
        )
        assert resp.status_code == 422

    def test_trocar_cliente_valida_acesso(
        self, client, csrf_de, advogada, criar_cliente, criar_caso, conceder_acesso
    ):
        cliente_novo = criar_cliente(nome="Novo cliente")
        # cliente visivel a advogada atraves de um caso autorizado
        base = criar_caso(cliente_id=cliente_novo.id)
        conceder_acesso(base, advogada)

        caso_alheio = criar_caso()  # sem cliente vinculado e de outro advogado
        # comum nao consegue apontar o caso dele para cliente que nao ve
        resp_comum = client.patch(
            f"/api/casos/{base.id}",
            headers={CSRF: csrf_de(PADRAO)},
            json={"cliente_id": 99999},
        )
        assert resp_comum.status_code in (403, 404)

        # admin troca o cliente e o espelho (coluna texto) acompanha
        resp = client.patch(
            f"/api/casos/{caso_alheio.id}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"cliente_id": cliente_novo.id},
        )
        assert resp.status_code == 200
        assert resp.json()["cliente_id"] == cliente_novo.id
        assert resp.json()["cliente"] == "Novo cliente"

    def test_cliente_inexistente_na_troca_404(self, client, csrf_de, criar_caso):
        caso = criar_caso()
        resp = client.patch(
            f"/api/casos/{caso.id}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"cliente_id": 99999},
        )
        assert resp.status_code == 404

    def test_data_abertura_futura_422(self, client, csrf_de, criar_caso):
        caso = criar_caso()
        futura = (date.today() + timedelta(days=10)).isoformat()
        resp = client.patch(
            f"/api/casos/{caso.id}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"data_abertura": futura},
        )
        assert resp.status_code == 422

    def test_atualizacao_sem_alteracao_nao_grava(
        self, client, csrf_de, criar_caso, db_session
    ):
        """Payload com os mesmos valores nao gera registro de auditoria."""
        from app.models.caso_historico import CasoHistorico

        caso = criar_caso(status="EM_ANDAMENTO")
        client.patch(
            f"/api/casos/{caso.id}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"status": "EM_ANDAMENTO"},
        )
        db_session.expire_all()
        registros = (
            db_session.query(CasoHistorico)
            .filter(CasoHistorico.caso_id == caso.id, CasoHistorico.operacao == "ATUALIZACAO")
            .count()
        )
        assert registros == 0


# ------------------------------------------------------------- arquivamento


class TestArquivamento:
    def test_admin_arquiva_200_e_registra(self, client, csrf_de, criar_caso, db_session):
        caso = criar_caso()
        resp = client.post(
            f"/api/casos/{caso.id}/arquivar", headers={CSRF: csrf_de(ADMIN)}
        )
        assert resp.status_code == 200, resp.text
        corpo = resp.json()
        assert corpo["arquivado"] is True
        assert corpo["arquivado_em"] is not None

        # novamente: 409 (operacao nao repetida)
        repetido = client.post(
            f"/api/casos/{caso.id}/arquivar", headers={CSRF: csrf_de(ADMIN)}
        )
        assert repetido.status_code == 409

    def test_comum_nao_arquiva_403(self, client, csrf_de, advogada, criar_caso, conceder_acesso):
        caso = criar_caso()
        conceder_acesso(caso, advogada)
        resp = client.post(
            f"/api/casos/{caso.id}/arquivar", headers={CSRF: csrf_de(PADRAO)}
        )
        assert resp.status_code == 403

    def test_arquivar_caso_inexistente_404(self, client, csrf_de):
        resp = client.post("/api/casos/99999/arquivar", headers={CSRF: csrf_de(ADMIN)})
        assert resp.status_code == 404

    def test_caso_arquivado_sai_da_listagem_padrao(
        self, client, csrf_de, criar_caso
    ):
        caso = criar_caso()
        client.post(f"/api/casos/{caso.id}/arquivar", headers={CSRF: csrf_de(ADMIN)})

        padrao = client.get("/api/casos")
        assert padrao.json()["total"] == 0
        assert caso.id not in _ids(padrao)

        arquivados = client.get("/api/casos/arquivados")
        assert arquivados.status_code == 200
        assert arquivados.json()["total"] == 1
        assert caso.id in _ids(arquivados)

    def test_arquivados_respeitam_escopo(self, client, csrf_de, advogada, criar_caso, conceder_acesso):
        meu = criar_caso(cliente="Meu")
        alheio = criar_caso(cliente="Alheio")
        conceder_acesso(meu, advogada)
        admin_csrf = csrf_de(ADMIN)
        client.post(f"/api/casos/{meu.id}/arquivar", headers={CSRF: admin_csrf})
        client.post(f"/api/casos/{alheio.id}/arquivar", headers={CSRF: admin_csrf})

        # admin ve os dois arquivados; comum so o seu
        assert client.get("/api/casos/arquivados?limite=100").json()["total"] == 2
        csrf_de(PADRAO)
        comum = client.get("/api/casos/arquivados")
        assert comum.json()["total"] == 1
        assert _ids(comum) == {meu.id}

    def test_relacionamentos_preservados_apos_arquivar(
        self, client, csrf_de, advogada, criar_caso, conceder_acesso, db_session
    ):
        """Soft delete: prazos, andamentos e acessos permanecem intactos."""
        from datetime import date as date_cls

        from app.models.andamento import Andamento
        from app.models.prazo import Prazo
        from app.models.usuario_caso import UsuarioCaso

        caso = criar_caso()
        linha = conceder_acesso(caso, advogada)
        db_session.add(
            Prazo(caso_id=caso.id, titulo="Prazo do caso", data_limite=date_cls.today())
        )
        db_session.add(
            Andamento(
                caso_id=caso.id,
                titulo="Peticao inicial",
                descricao="Peticao inicial protocolada",
            )
        )
        db_session.commit()

        resp = client.post(f"/api/casos/{caso.id}/arquivar", headers={CSRF: csrf_de(ADMIN)})
        assert resp.status_code == 200
        db_session.expire_all()

        assert db_session.query(Prazo).filter_by(caso_id=caso.id).count() == 1
        assert db_session.query(Andamento).filter_by(caso_id=caso.id).count() == 1
        acesso = db_session.get(UsuarioCaso, linha.id)
        assert acesso is not None and acesso.ativo is True

        # detalhe do caso arquivado continua acessivel (mantem o historico)
        resp_detalhe = client.get(f"/api/casos/{caso.id}")
        assert resp_detalhe.status_code == 200
        assert resp_detalhe.json()["arquivado"] is True

    def test_sem_sessao_401(self, client, criar_caso):
        caso = criar_caso()
        assert client.post(f"/api/casos/{caso.id}/arquivar").status_code == 401
        assert client.get("/api/casos/arquivados").status_code == 401


# ------------------------------------------------------------------ historico


class TestHistorico:
    def test_criacao_gera_registro(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Auditoria")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente_id=cliente.id)
        resp = client.get(f"/api/casos/{caso['id']}/historico")
        assert resp.status_code == 200
        registros = resp.json()
        assert len(registros) == 1
        assert registros[0]["operacao"] == "CRIACAO"

    def test_atualizacao_registra_campos_alterados(
        self, client, csrf_de, criar_caso
    ):
        caso = criar_caso()
        csrf = csrf_de(ADMIN)
        client.patch(
            f"/api/casos/{caso.id}",
            headers={CSRF: csrf},
            json={"titulo": "Novo titulo", "prioridade": "URGENTE"},
        )
        registros = client.get(f"/api/casos/{caso.id}/historico").json()
        atualizacao = next(r for r in registros if r["operacao"] == "ATUALIZACAO")
        dados = atualizacao["dados"]
        assert set(dados) == {"titulo", "prioridade"}
        assert dados["prioridade"]["depois"] == "URGENTE"
        assert "senha" not in str(dados).lower()  # nada sensivel no historico

    def test_arquivamento_registra_operacao(self, client, csrf_de, criar_caso):
        caso = criar_caso()
        client.post(f"/api/casos/{caso.id}/arquivar", headers={CSRF: csrf_de(ADMIN)})
        registros = client.get(f"/api/casos/{caso.id}/historico").json()
        assert any(r["operacao"] == "ARQUIVAMENTO" for r in registros)

    def test_historico_respeita_escopo(self, client, csrf_de, advogada, criar_caso, conceder_acesso):
        meu = criar_caso()
        alheio = criar_caso()
        conceder_acesso(meu, advogada)
        csrf_de(ADMIN)
        assert client.get(f"/api/casos/{alheio.id}/historico").status_code == 200

        csrf_de(PADRAO)
        assert client.get(f"/api/casos/{meu.id}/historico").status_code == 200
        assert client.get(f"/api/casos/{alheio.id}/historico").status_code == 404

    def test_historico_nao_tem_escrita(self, client, csrf_de, criar_caso):
        """Nao existe endpoint para alterar o historico."""
        caso = criar_caso()
        csrf = csrf_de(ADMIN)
        assert client.post(
            f"/api/casos/{caso.id}/historico", headers={CSRF: csrf}, json={}
        ).status_code in (404, 405)
        assert client.delete(
            f"/api/casos/{caso.id}/historico", headers={CSRF: csrf}
        ).status_code in (404, 405)

    def test_quem_registrou_a_operacao(self, client, csrf_de, criar_cliente, admin):
        cliente = criar_cliente(nome="Auditor op")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente_id=cliente.id)
        registros = client.get(f"/api/casos/{caso['id']}/historico").json()
        assert registros[0]["usuario_id"] == admin.id
