"""Testes da Fase 3: gerenciamento de processos judiciais.

Cobrem as regras de negocio exigidas: validacao CNJ real (digitos
verificadores), vinculo N:1 com o caso, escopo de acesso da Fase 1 (um
processo nunca da acesso a caso alheio), permissoes de escrita (admin,
responsavel ou grant `pode_gerenciar_processos`), arquivamento proprio do
processo, auditoria e preservacao dos dados legados de `Caso.numero_processo`.
"""

from datetime import date, timedelta

import pytest

from tests.conftest import ADMIN, FUNCIONARIO, PADRAO, gerar_numero_cnj

CSRF = "X-CSRF-Token"


def _numero(seq: int) -> str:
    """Numero CNJ valido (digitos verificadores conferem) para o teste."""
    return gerar_numero_cnj(seq)


def _criar_caso_api(client, csrf, cliente_id, **dados):
    payload = {"titulo": "Caso da Fase 3", "cliente_id": cliente_id}
    payload.update(dados)
    resp = client.post("/api/casos", headers={CSRF: csrf}, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _criar_processo(client, csrf, caso_id, *, seq=1, **dados):
    """Cadastra um processo no caso e devolve o corpo (201)."""
    payload = {"numero_processo": _numero(seq)}
    payload.update(dados)
    resp = client.post(
        f"/api/casos/{caso_id}/processos", headers={CSRF: csrf}, json=payload
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ------------------------------------------------------- validacao CNJ (unit)


class TestValidacaoCNJ:
    """O numero e validado pelos digitos verificadores (modulo 97), nao regex."""

    def test_numero_do_seed_legado_nao_passa_na_validacao(self):
        from app.core.validacao import eh_cnj

        # os numeros legados do seed tem DD arbitrario - nao sao CNJ validos
        assert not eh_cnj("00012345620258260100")

    def test_gerador_produz_numero_valido(self):
        from app.core.validacao import eh_cnj

        for seq in range(1, 6):
            assert eh_cnj(_numero(seq).replace(".", "").replace("-", ""))

    def test_tamanho_errado_e_invalido(self):
        from app.core.validacao import eh_cnj

        assert not eh_cnj("0000001352026826010")  # 19 digitos
        assert not eh_cnj("000000135202682601000")  # 21 digitos

    def test_digitos_todos_iguais_sao_invalidos(self):
        from app.core.validacao import eh_cnj

        assert not eh_cnj("1" * 20)

    def test_normalizar_aceita_com_e_sem_mascara(self):
        from app.core.validacao import normalizar_numero_processo

        esperado = "00000013520268260100"
        assert normalizar_numero_processo("0000001-35.2026.8.26.0100") == esperado
        assert normalizar_numero_processo(esperado) == esperado

    def test_normalizar_rejeita_dd_incorreto(self):
        from app.core.validacao import (
            NumeroProcessoInvalidoError,
            normalizar_numero_processo,
        )

        # mesmo formato, mas DD nao confere (modulo 97)
        with pytest.raises(NumeroProcessoInvalidoError):
            normalizar_numero_processo("0001234-56.2025.8.26.0100")

    def test_formatar_e_roundtrip(self):
        from app.core.validacao import (
            formatar_numero_processo,
            normalizar_numero_processo,
        )

        mascara = "0000001-35.2026.8.26.0100"
        normalizado = normalizar_numero_processo(mascara)
        assert formatar_numero_processo(normalizado) == mascara
        assert formatar_numero_processo(normalizar_numero_processo(mascara)) == mascara


# --------------------------------------------------------------- cadastro


class TestCadastroProcessos:
    def test_cadastro_valido_201_admin(self, client, csrf_de, criar_cliente):
        """Numero normalizado no banco + formatado na resposta + criador."""
        cliente = criar_cliente(nome="Cliente Processo")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        resp = client.post(
            f"/api/casos/{caso['id']}/processos",
            headers={CSRF: csrf_de(ADMIN)},
            json={
                "numero_processo": _numero(1),  # com mascara
                "tribunal": "TJSP",
                "orgao_julgador": "1a Vara Civel",
                "comarca": "Sao Paulo",
                "instancia": "PRIMEIRA_INSTANCIA",
                "classe_processual": "Acao de Cobranca",
                "assunto": "Cobranca indevida de tarifas",
                "data_distribuicao": "2026-01-15",
                "status": "EM_ANDAMENTO",
                "valor_causa": 50000.00,
                "segredo_justica": False,
                "observacoes": "Audiencia marcada",
            },
        )
        assert resp.status_code == 201, resp.text
        corpo = resp.json()
        assert corpo["caso_id"] == caso["id"]
        # armazenado normalizado (20 digitos) e exibido formatado
        assert corpo["numero_processo"] == _numero(1).replace(".", "").replace("-", "")
        assert len(corpo["numero_processo"]) == 20
        assert corpo["numero_formatado"] == _numero(1)
        assert corpo["status"] == "EM_ANDAMENTO"
        assert float(corpo["valor_causa"]) == 50000.0
        assert corpo["data_distribuicao"] == "2026-01-15"
        assert corpo["instancia"] == "PRIMEIRA_INSTANCIA"
        assert corpo["arquivado"] is False
        assert corpo["criado_por"] is not None  # operador registrado
        assert corpo["criado_por_nome"] == ADMIN["nome"]
        assert "senha" not in resp.text

    def test_cadastro_aceita_numero_sem_mascara(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Sem Mascara")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        corpo = _criar_processo(
            client, csrf_de(ADMIN), caso["id"], numero_processo=_numero(2)
        )
        assert corpo["numero_processo"] == _numero(2).replace(".", "").replace("-", "")

    def test_status_padrao_distribuido(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Padrao Status")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        corpo = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=3)
        assert corpo["status"] == "DISTRIBUIDO"
        assert corpo["segredo_justica"] is False

    def test_numero_cnj_invalido_422(self, client, csrf_de, criar_cliente):
        """DD nao confere (modulo 97) - regex pura deixaria passar."""
        cliente = criar_cliente(nome="DD Errado")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        resp = client.post(
            f"/api/casos/{caso['id']}/processos",
            headers={CSRF: csrf_de(ADMIN)},
            json={"numero_processo": "0001234-56.2025.8.26.0100"},
        )
        assert resp.status_code == 422, resp.text

    def test_numero_com_muito_poucos_digitos_422(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Curto")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        resp = client.post(
            f"/api/casos/{caso['id']}/processos",
            headers={CSRF: csrf_de(ADMIN)},
            json={"numero_processo": "123"},
        )
        assert resp.status_code == 422

    def test_numero_duplicado_409(self, client, csrf_de, criar_cliente):
        """Mesmo CNJ em outro caso: 409 (unicidade global no banco)."""
        cliente = criar_cliente(nome="Duplicado")
        caso_a = _criar_caso_api(client, csrf_de(ADMIN), cliente.id, titulo="Caso A")
        caso_b = _criar_caso_api(client, csrf_de(ADMIN), cliente.id, titulo="Caso B")
        _criar_processo(client, csrf_de(ADMIN), caso_a["id"], seq=4)
        resp = client.post(
            f"/api/casos/{caso_b['id']}/processos",
            headers={CSRF: csrf_de(ADMIN)},
            json={"numero_processo": _numero(4)},
        )
        assert resp.status_code == 409, resp.text

    def test_numero_duplicado_no_mesmo_caso_409(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Duplicado Mesmo")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=5)
        resp = client.post(
            f"/api/casos/{caso['id']}/processos",
            headers={CSRF: csrf_de(ADMIN)},
            json={"numero_processo": _numero(5)},
        )
        assert resp.status_code == 409

    def test_caso_inexistente_404(self, client, csrf_de):
        resp = client.post(
            "/api/casos/99999/processos",
            headers={CSRF: csrf_de(ADMIN)},
            json={"numero_processo": _numero(6)},
        )
        assert resp.status_code == 404

    def test_caso_arquivado_nao_recebe_novo_processo_422(
        self, client, csrf_de, criar_cliente
    ):
        """Arquivamento do CASO impede novos processos (422), e e distinto do
        arquivamento do processo."""
        cliente = criar_cliente(nome="Caso Arquivado")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        arch = client.post(
            f"/api/casos/{caso['id']}/arquivar", headers={CSRF: csrf_de(ADMIN)}
        )
        assert arch.status_code == 200, arch.text
        resp = client.post(
            f"/api/casos/{caso['id']}/processos",
            headers={CSRF: csrf_de(ADMIN)},
            json={"numero_processo": _numero(7)},
        )
        assert resp.status_code == 422, resp.text

    def test_usuario_sem_acesso_ao_caso_404(
        self, client, csrf_de, advogada, criar_cliente
    ):
        """Fora do escopo da Fase 1: mesmo codigo do caso inexistente."""
        cliente = criar_cliente(nome="Escopo")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        resp = client.post(
            f"/api/casos/{caso['id']}/processos",
            headers={CSRF: csrf_de(PADRAO)},
            json={"numero_processo": _numero(8)},
        )
        assert resp.status_code == 404

    def test_funcionario_com_acesso_mas_sem_permissao_403(
        self, client, csrf_de, funcionario, criar_caso, conceder_acesso
    ):
        """Visualizar nao e gerenciar: funcionario sem grant leva 403."""
        caso = criar_caso()
        conceder_acesso(caso, funcionario)  # so pode_visualizar
        resp = client.post(
            f"/api/casos/{caso.id}/processos",
            headers={CSRF: csrf_de(FUNCIONARIO)},
            json={"numero_processo": _numero(9)},
        )
        assert resp.status_code == 403, resp.text

    def test_funcionario_com_grant_processos_cadastra_201(
        self, client, csrf_de, funcionario, criar_caso, conceder_acesso
    ):
        """A concessao `pode_gerenciar_processos` habilita o funcionario."""
        caso = criar_caso()
        conceder_acesso(caso, funcionario, pode_gerenciar_processos=True)
        resp = client.post(
            f"/api/casos/{caso.id}/processos",
            headers={CSRF: csrf_de(FUNCIONARIO)},
            json={"numero_processo": _numero(10)},
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["criado_por"] == funcionario.id

    def test_advogado_responsavel_cadastra_201(
        self, client, csrf_de, advogada, criar_cliente
    ):
        """Responsavel pelo caso pode cadastrar processos dele."""
        cliente = criar_cliente(nome="Responsavel")
        caso = _criar_caso_api(
            client, csrf_de(ADMIN), cliente.id, responsavel_id=advogada.id
        )
        resp = client.post(
            f"/api/casos/{caso['id']}/processos",
            headers={CSRF: csrf_de(PADRAO)},
            json={"numero_processo": _numero(11)},
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["criado_por"] == advogada.id

    def test_advogado_com_grant_processos_cadastra_201(
        self, client, csrf_de, advogada, criar_caso, conceder_acesso
    ):
        caso = criar_caso()
        conceder_acesso(caso, advogada, pode_gerenciar_processos=True)
        resp = client.post(
            f"/api/casos/{caso.id}/processos",
            headers={CSRF: csrf_de(PADRAO)},
            json={"numero_processo": _numero(12)},
        )
        assert resp.status_code == 201, resp.text

    def test_grant_revogado_nao_dacesso_404(
        self, client, csrf_de, funcionario, criar_caso, conceder_acesso, db_session
    ):
        """Linha revogada sai do escopo de leitura (404), nao so da escrita."""
        caso = criar_caso()
        linha = conceder_acesso(caso, funcionario, pode_gerenciar_processos=True)
        linha.ativo = False
        db_session.commit()
        resp = client.post(
            f"/api/casos/{caso.id}/processos",
            headers={CSRF: csrf_de(FUNCIONARIO)},
            json={"numero_processo": _numero(13)},
        )
        assert resp.status_code == 404

    def test_payload_nao_aceita_caso_id_criado_por_cliente(
        self, client, csrf_de, criar_cliente
    ):
        """extra=forbid: nao ha como 'migrar' processo nem vincular cliente."""
        cliente = criar_cliente(nome="Payload")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        csrf = csrf_de(ADMIN)
        for proibido in (
            {"caso_id": 999},
            {"criado_por": 1},
            {"cliente_id": 1},
            {"arquivado": True},
        ):
            payload = {"numero_processo": _numero(14), **proibido}
            resp = client.post(
                f"/api/casos/{caso['id']}/processos",
                headers={CSRF: csrf},
                json=payload,
            )
            assert resp.status_code == 422, (proibido, resp.text)

    def test_data_distribuicao_futura_422(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Data Futura")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        futura = (date.today() + timedelta(days=3)).isoformat()
        resp = client.post(
            f"/api/casos/{caso['id']}/processos",
            headers={CSRF: csrf_de(ADMIN)},
            json={"numero_processo": _numero(15), "data_distribuicao": futura},
        )
        assert resp.status_code == 422, resp.text

    def test_valor_causa_negativo_422(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Valor Negativo")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        resp = client.post(
            f"/api/casos/{caso['id']}/processos",
            headers={CSRF: csrf_de(ADMIN)},
            json={"numero_processo": _numero(16), "valor_causa": -100},
        )
        assert resp.status_code == 422

    def test_instancia_invalida_422(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Instancia")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        resp = client.post(
            f"/api/casos/{caso['id']}/processos",
            headers={CSRF: csrf_de(ADMIN)},
            json={"numero_processo": _numero(17), "instancia": "TERCEIRA"},
        )
        assert resp.status_code == 422

    def test_status_invalido_422(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Status")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        resp = client.post(
            f"/api/casos/{caso['id']}/processos",
            headers={CSRF: csrf_de(ADMIN)},
            json={"numero_processo": _numero(18), "status": "QUALQUER"},
        )
        assert resp.status_code == 422

    def test_sem_sessao_401(self, client, criar_cliente):
        cliente = criar_cliente(nome="Sem Sessao")
        resp = client.post(
            "/api/casos/1/processos", json={"numero_processo": _numero(19)}
        )
        assert resp.status_code == 401

    def test_sem_csrf_403(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Sem CSRF")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        resp = client.post(
            f"/api/casos/{caso['id']}/processos",
            json={"numero_processo": _numero(20)},
        )
        assert resp.status_code == 403


# ------------------------------------------------------- consulta e listagem


class TestConsultaProcessos:
    def test_detalhe_processo_200(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Detalhe")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        criado = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        resp = client.get(f"/api/processos/{criado['id']}")
        assert resp.status_code == 200, resp.text
        corpo = resp.json()
        assert corpo["id"] == criado["id"]
        assert corpo["numero_formatado"] == _numero(1)
        assert corpo["caso_id"] == caso["id"]

    def test_detalhe_inexistente_404(self, client, csrf_de):
        csrf_de(ADMIN)
        assert client.get("/api/processos/99999").status_code == 404

    def test_processo_de_caso_alheio_404(
        self, client, csrf_de, advogada, criar_cliente
    ):
        """Nunca acesso indireto a caso nao autorizado (mesmo codigo do 404)."""
        cliente = criar_cliente(nome="Alheio")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        criado = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        csrf_de(PADRAO)  # loga advogada sem grant
        resp = client.get(f"/api/processos/{criado['id']}")
        assert resp.status_code == 404

    def test_listagem_por_caso(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Por Caso")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=2)
        resp = client.get(f"/api/casos/{caso['id']}/processos")
        assert resp.status_code == 200, resp.text
        itens = resp.json()
        assert len(itens) == 2
        assert {i["numero_processo"] for i in itens} == {
            _numero(1).replace(".", "").replace("-", ""),
            _numero(2).replace(".", "").replace("-", ""),
        }

    def test_listagem_caso_alheio_404(self, client, csrf_de, advogada, criar_caso):
        caso = criar_caso()
        resp = client.get(
            f"/api/casos/{caso.id}/processos", headers={CSRF: csrf_de(PADRAO)}
        )
        assert resp.status_code == 404

    def test_caso_sem_processos_lista_vazia(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Vazio")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        resp = client.get(f"/api/casos/{caso['id']}/processos")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_listagem_geral_paginacao_no_banco(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="Paginado")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        for seq in (1, 2, 3):
            _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=seq)

        p1 = client.get("/api/processos?pagina=1&limite=2")
        assert p1.status_code == 200, p1.text
        corpo1 = p1.json()
        assert corpo1["total"] == 3
        assert corpo1["pagina"] == 1
        assert corpo1["limite"] == 2
        assert len(corpo1["itens"]) == 2

        p2 = client.get("/api/processos?pagina=2&limite=2")
        corpo2 = p2.json()
        assert corpo2["total"] == 3
        assert len(corpo2["itens"]) == 1
        # paginas disjuntas (ordenacao estavel no banco)
        ids1 = {i["id"] for i in corpo1["itens"]}
        ids2 = {i["id"] for i in corpo2["itens"]}
        assert not ids1 & ids2
        assert len(ids1 | ids2) == 3

    def test_filtros_de_pesquisa(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Filtros")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        csrf = csrf_de(ADMIN)
        _criar_processo(
            client,
            csrf,
            caso["id"],
            seq=1,
            tribunal="TJSP",
            comarca="Sao Paulo",
            instancia="PRIMEIRA_INSTANCIA",
            classe_processual="Acao de Cobranca",
            status="EM_ANDAMENTO",
            data_distribuicao="2026-01-10",
        )
        _criar_processo(
            client,
            csrf,
            caso["id"],
            seq=2,
            tribunal="TJRJ",
            comarca="Rio de Janeiro",
            instancia="SEGUNDA_INSTANCIA",
            classe_processual="Apelacao",
            status="SUSPENSO",
            data_distribuicao="2026-02-20",
        )

        def busca(params):
            resp = client.get(f"/api/processos?{params}")
            assert resp.status_code == 200, resp.text
            return {i["numero_processo"] for i in resp.json()["itens"]}

        n1 = _numero(1).replace(".", "").replace("-", "")
        n2 = _numero(2).replace(".", "").replace("-", "")

        assert busca("tribunal=TJSP") == {n1}
        assert busca("comarca=Rio") == {n2}
        assert busca("instancia=SEGUNDA_INSTANCIA") == {n2}
        assert busca("classe_processual=Apelacao") == {n2}
        assert busca("status=SUSPENSO") == {n2}
        assert busca("distribuicao_de=2026-02-01&distribuicao_ate=2026-03-01") == {n2}
        assert busca("distribuicao_ate=2026-01-31") == {n1}
        # busca pelo numero CNJ (aceita com mascara ou so digitos)
        assert busca(f"q={_numero(1)}") == {n1}
        assert busca(f"q={n1[:7]}") == {n1}
        # termo sem digitos nao casa com todos os numeros
        assert busca("q=abc") == set()
        # filtro por caso
        assert busca(f"caso_id={caso['id']}") == {n1, n2}

    def test_listagem_respeita_escopo(
        self, client, csrf_de, advogada, criar_cliente, criar_caso, conceder_acesso, db_session
    ):
        """Filtros e paginacao nunca burlam o escopo da Fase 1."""
        from app.core.validacao import normalizar_numero_processo
        from app.models.processo_judicial import ProcessoJudicial

        cliente = criar_cliente(nome="Visivel")
        meu_caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id, titulo="Meu")
        _criar_processo(client, csrf_de(ADMIN), meu_caso["id"], seq=1)

        # caso com grant para a advogada + processo dele
        alheio = criar_caso(cliente="Do meu acesso")
        conceder_acesso(alheio, advogada)
        proc_alheio = ProcessoJudicial(
            caso_id=alheio.id,
            numero_processo=normalizar_numero_processo(_numero(2)),
            status="EM_ANDAMENTO",
            segredo_justica=False,
            arquivado=False,
        )
        db_session.add(proc_alheio)
        db_session.commit()

        # caso SEM grant para a advogada + processo dele (nao pode ver)
        sem_grant = criar_caso(cliente="Sem grant")
        proc_sem_grant = ProcessoJudicial(
            caso_id=sem_grant.id,
            numero_processo=normalizar_numero_processo(_numero(3)),
            status="EM_ANDAMENTO",
            segredo_justica=False,
            arquivado=False,
        )
        db_session.add(proc_sem_grant)
        db_session.commit()

        csrf = csrf_de(PADRAO)
        todos = client.get("/api/processos?limite=100")
        assert todos.status_code == 200
        visiveis = {i["numero_processo"] for i in todos.json()["itens"]}
        # a advogada ve apenas o processo do caso com grant ativo
        assert visiveis == {normalizar_numero_processo(_numero(2))}
        # tentativas de contorno pelo filtro de caso alheio
        por_caso = client.get(f"/api/processos?caso_id={sem_grant.id}")
        assert por_caso.json()["total"] == 0
        # busca pelo numero do processo alheio nao vaza
        busca = client.get(
            f"/api/processos?q={normalizar_numero_processo(_numero(3))}"
        )
        assert busca.json()["total"] == 0

    def test_arquivados_fora_da_listagem_padrao(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="Arquivado")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        csrf = csrf_de(ADMIN)
        proc = _criar_processo(client, csrf, caso["id"], seq=1)
        _criar_processo(client, csrf, caso["id"], seq=2)

        arch = client.post(f"/api/processos/{proc['id']}/arquivar", headers={CSRF: csrf})
        assert arch.status_code == 200, arch.text

        geral = client.get("/api/processos?limite=100")
        ativos = {i["id"] for i in geral.json()["itens"]}
        assert proc["id"] not in ativos
        assert geral.json()["total"] == 1

        arquivados = client.get("/api/processos?arquivados=true&limite=100")
        assert {i["id"] for i in arquivados.json()["itens"]} == {proc["id"]}

        # por caso: some da listagem padrao, volta com incluir_arquivados
        por_caso = client.get(f"/api/casos/{caso['id']}/processos")
        assert proc["id"] not in {i["id"] for i in por_caso.json()}
        assert len(por_caso.json()) == 1
        com_arch = client.get(
            f"/api/casos/{caso['id']}/processos?incluir_arquivados=true"
        )
        assert proc["id"] in {i["id"] for i in com_arch.json()}

        # arquivado continua consultavel por id (historico preservado)
        detalhe = client.get(f"/api/processos/{proc['id']}")
        assert detalhe.status_code == 200
        assert detalhe.json()["arquivado"] is True


# -------------------------------------------------------------- atualizacao


class TestAtualizacaoProcessos:
    def test_admin_atualiza_qualquer_processo(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Atualiza")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        proc = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        resp = client.patch(
            f"/api/processos/{proc['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"tribunal": "TJMG", "comarca": "Belo Horizonte"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["tribunal"] == "TJMG"
        assert resp.json()["comarca"] == "Belo Horizonte"

    def test_responsavel_atualiza_o_proprio_processo(
        self, client, csrf_de, advogada, criar_cliente
    ):
        cliente = criar_cliente(nome="Resp")
        caso = _criar_caso_api(
            client, csrf_de(ADMIN), cliente.id, responsavel_id=advogada.id
        )
        proc = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        resp = client.patch(
            f"/api/processos/{proc['id']}",
            headers={CSRF: csrf_de(PADRAO)},
            json={"assunto": "Revisado pela responsavel"},
        )
        assert resp.status_code == 200, resp.text

    def test_funcionario_com_grant_atualiza_201(
        self, client, csrf_de, funcionario, criar_caso, conceder_acesso
    ):
        caso = criar_caso()
        conceder_acesso(caso, funcionario, pode_gerenciar_processos=True)
        proc = _criar_processo(client, csrf_de(ADMIN), caso.id, seq=1)
        resp = client.patch(
            f"/api/processos/{proc['id']}",
            headers={CSRF: csrf_de(FUNCIONARIO)},
            json={"observacoes": "Atualizado pelo funcionario"},
        )
        assert resp.status_code == 200, resp.text

    def test_funcionario_sem_grant_nao_atualiza_403(
        self, client, csrf_de, funcionario, criar_caso, conceder_acesso
    ):
        caso = criar_caso()
        conceder_acesso(caso, funcionario)  # so visualizar
        proc = _criar_processo(client, csrf_de(ADMIN), caso.id, seq=1)
        resp = client.patch(
            f"/api/processos/{proc['id']}",
            headers={CSRF: csrf_de(FUNCIONARIO)},
            json={"observacoes": "Nao deveria passar"},
        )
        assert resp.status_code == 403

    def test_processo_de_caso_alheio_404(
        self, client, csrf_de, advogada, criar_cliente
    ):
        cliente = criar_cliente(nome="Alheio Patch")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        proc = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        resp = client.patch(
            f"/api/processos/{proc['id']}",
            headers={CSRF: csrf_de(PADRAO)},
            json={"tribunal": "TJXX"},
        )
        assert resp.status_code == 404

    def test_payload_nao_aceita_alterar_caso_id(
        self, client, csrf_de, criar_cliente
    ):
        """extra=forbid: o vinculo vem da URL, nao do payload comum."""
        cliente = criar_cliente(nome="Caso Trocado")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id, titulo="Origem")
        outro = _criar_caso_api(client, csrf_de(ADMIN), cliente.id, titulo="Destino")
        proc = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        resp = client.patch(
            f"/api/processos/{proc['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"caso_id": outro["id"]},
        )
        assert resp.status_code == 422, resp.text
        # e o processo continua no caso de origem
        detalhe = client.get(f"/api/processos/{proc['id']}")
        assert detalhe.json()["caso_id"] == caso["id"]

    def test_payload_nao_aceita_alterar_criado_por(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="Criador")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        proc = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        resp = client.patch(
            f"/api/processos/{proc['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"criado_por": 999},
        )
        assert resp.status_code == 422
        detalhe = client.get(f"/api/processos/{proc['id']}")
        assert detalhe.json()["criado_por"] == proc["criado_por"]

    def test_numero_alterado_e_revalidado_e_normalizado(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="Renomeia")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        proc = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        novo = _numero(2)
        resp = client.patch(
            f"/api/processos/{proc['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"numero_processo": novo},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["numero_processo"] == novo.replace(".", "").replace("-", "")
        assert resp.json()["numero_formatado"] == novo

    def test_numero_invalido_na_atualizacao_422(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="DD Ruim")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        proc = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        resp = client.patch(
            f"/api/processos/{proc['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"numero_processo": "0001234-56.2025.8.26.0100"},
        )
        assert resp.status_code == 422

    def test_numero_duplicado_na_atualizacao_409(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="Duplica Update")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id, titulo="Um caso")
        outro = _criar_caso_api(client, csrf_de(ADMIN), cliente.id, titulo="Dois caso")
        _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        alvo = _criar_processo(client, csrf_de(ADMIN), outro["id"], seq=2)
        resp = client.patch(
            f"/api/processos/{alvo['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"numero_processo": _numero(1)},
        )
        assert resp.status_code == 409, resp.text

    def test_numero_mesmo_nao_dispara_conflito(
        self, client, csrf_de, criar_cliente
    ):
        """Reenviar o proprio numero nao e duplicidade (nao colidir consigo)."""
        cliente = criar_cliente(nome="Mesmo Numero")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        proc = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        resp = client.patch(
            f"/api/processos/{proc['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"numero_processo": _numero(1)},
        )
        assert resp.status_code == 200, resp.text

    def test_atualizacao_sem_alteracao_nao_grava_historico(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="Igual")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        proc = _criar_processo(
            client, csrf_de(ADMIN), caso["id"], seq=1, tribunal="TJSP"
        )
        resp = client.patch(
            f"/api/processos/{proc['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"tribunal": "TJSP"},
        )
        assert resp.status_code == 200
        hist = client.get(f"/api/processos/{proc['id']}/historico")
        assert [h["operacao"] for h in hist.json()] == ["CRIACAO"]


# ------------------------------------------------------------------- status


class TestStatusProcesso:
    def test_mudar_status_200(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Status")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        proc = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        resp = client.patch(
            f"/api/processos/{proc['id']}/status",
            headers={CSRF: csrf_de(ADMIN)},
            json={"status": "SENTENCA_PROFERIDA"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "SENTENCA_PROFERIDA"

    def test_encerramento_baixado(
        self, client, csrf_de, criar_cliente
    ):
        """Encerramento (BAIXADO/EXTINTO) via status, com auditoria."""
        cliente = criar_cliente(nome="Encerra")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        proc = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        resp = client.patch(
            f"/api/processos/{proc['id']}/status",
            headers={CSRF: csrf_de(ADMIN)},
            json={"status": "BAIXADO"},
        )
        assert resp.status_code == 200
        hist = client.get(f"/api/processos/{proc['id']}/historico")
        mudancas = [h for h in hist.json() if h["operacao"] == "MUDANCA_STATUS"]
        assert len(mudancas) == 1
        assert mudancas[0]["dados"]["status"] == {
            "antes": "DISTRIBUIDO",
            "depois": "BAIXADO",
        }

    def test_status_invalido_422(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Status Ruim")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        proc = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        resp = client.patch(
            f"/api/processos/{proc['id']}/status",
            headers={CSRF: csrf_de(ADMIN)},
            json={"status": "SUMIU"},
        )
        assert resp.status_code == 422

    def test_status_igual_nao_grava_historico(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="Mesmo Status")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        proc = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        resp = client.patch(
            f"/api/processos/{proc['id']}/status",
            headers={CSRF: csrf_de(ADMIN)},
            json={"status": "DISTRIBUIDO"},
        )
        assert resp.status_code == 200
        hist = client.get(f"/api/processos/{proc['id']}/historico")
        assert [h["operacao"] for h in hist.json()] == ["CRIACAO"]

    def test_funcionario_sem_grant_nao_muda_status_403(
        self, client, csrf_de, funcionario, criar_caso, conceder_acesso
    ):
        caso = criar_caso()
        conceder_acesso(caso, funcionario)
        proc = _criar_processo(client, csrf_de(ADMIN), caso.id, seq=1)
        resp = client.patch(
            f"/api/processos/{proc['id']}/status",
            headers={CSRF: csrf_de(FUNCIONARIO)},
            json={"status": "EXTINTO"},
        )
        assert resp.status_code == 403


# ------------------------------------------------------------- arquivamento


class TestArquivamentoProcesso:
    def test_arquivar_processo_200_e_registra(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="Arch")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        proc = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        resp = client.post(
            f"/api/processos/{proc['id']}/arquivar", headers={CSRF: csrf_de(ADMIN)}
        )
        assert resp.status_code == 200, resp.text
        corpo = resp.json()
        assert corpo["arquivado"] is True
        assert corpo["arquivado_em"] is not None

    def test_arquivar_de_novo_409(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Arch Duplo")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        proc = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        csrf = csrf_de(ADMIN)
        assert (
            client.post(
                f"/api/processos/{proc['id']}/arquivar", headers={CSRF: csrf}
            ).status_code
            == 200
        )
        resp = client.post(
            f"/api/processos/{proc['id']}/arquivar", headers={CSRF: csrf}
        )
        assert resp.status_code == 409, resp.text

    def test_arquivamento_e_do_processo_nao_do_caso(
        self, client, csrf_de, criar_cliente
    ):
        """Processo arquivado com caso ainda ativo (outras demandas)."""
        cliente = criar_cliente(nome="So Processo")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        p1 = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=2)

        resp = client.post(
            f"/api/processos/{p1['id']}/arquivar", headers={CSRF: csrf_de(ADMIN)}
        )
        assert resp.status_code == 200

        # caso continua ATIVO e com o outro processo
        detalhe_caso = client.get(f"/api/casos/{caso['id']}")
        assert detalhe_caso.status_code == 200
        assert detalhe_caso.json()["arquivado"] is False
        ativos = client.get(f"/api/casos/{caso['id']}/processos").json()
        assert len(ativos) == 1
        assert ativos[0]["id"] != p1["id"]

    def test_arquivamento_de_caso_nao_apaga_processos(
        self, client, csrf_de, criar_cliente
    ):
        """Arquivar o CASO preserva os processos (soft delete)."""
        cliente = criar_cliente(nome="Caso Arch")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        proc = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        resp = client.post(
            f"/api/casos/{caso['id']}/arquivar", headers={CSRF: csrf_de(ADMIN)}
        )
        assert resp.status_code == 200
        # processo segue consultavel
        detalhe = client.get(f"/api/processos/{proc['id']}")
        assert detalhe.status_code == 200
        assert detalhe.json()["caso_id"] == caso["id"]

    def test_funcionario_sem_grant_nao_arquiva_403(
        self, client, csrf_de, funcionario, criar_caso, conceder_acesso
    ):
        caso = criar_caso()
        conceder_acesso(caso, funcionario)
        proc = _criar_processo(client, csrf_de(ADMIN), caso.id, seq=1)
        resp = client.post(
            f"/api/processos/{proc['id']}/arquivar",
            headers={CSRF: csrf_de(FUNCIONARIO)},
        )
        assert resp.status_code == 403

    def test_processo_alheio_nao_arquiva_404(
        self, client, csrf_de, advogada, criar_cliente
    ):
        cliente = criar_cliente(nome="Alheio Arch")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        proc = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        resp = client.post(
            f"/api/processos/{proc['id']}/arquivar",
            headers={CSRF: csrf_de(PADRAO)},
        )
        assert resp.status_code == 404

    def test_sem_csrf_nao_arquiva_403(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="CSRF Arch")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        proc = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        resp = client.post(f"/api/processos/{proc['id']}/arquivar")
        assert resp.status_code == 403


# ---------------------------------------------------------------- historico


class TestHistoricoProcesso:
    def test_criacao_gera_registro(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Hist")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        proc = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        hist = client.get(f"/api/processos/{proc['id']}/historico")
        assert hist.status_code == 200, hist.text
        assert [h["operacao"] for h in hist.json()] == ["CRIACAO"]

    def test_atualizacao_registra_campos_alterados(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="Hist Update")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        proc = _criar_processo(
            client, csrf_de(ADMIN), caso["id"], seq=1, tribunal="TJSP"
        )
        client.patch(
            f"/api/processos/{proc['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"tribunal": "TJRS"},
        )
        hist = client.get(f"/api/processos/{proc['id']}/historico").json()
        atualizacao = [h for h in hist if h["operacao"] == "ATUALIZACAO"]
        assert len(atualizacao) == 1
        assert atualizacao[0]["dados"]["tribunal"] == {
            "antes": "TJSP",
            "depois": "TJRS",
        }

    def test_arquivamento_registra_operacao(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="Hist Arch")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        proc = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        client.post(
            f"/api/processos/{proc['id']}/arquivar", headers={CSRF: csrf_de(ADMIN)}
        )
        hist = client.get(f"/api/processos/{proc['id']}/historico").json()
        assert "ARQUIVAMENTO" in [h["operacao"] for h in hist]

    def test_historico_identifica_o_usuario(
        self, client, csrf_de, advogada, criar_cliente
    ):
        cliente = criar_cliente(nome="Quem")
        caso = _criar_caso_api(
            client, csrf_de(ADMIN), cliente.id, responsavel_id=advogada.id
        )
        proc = _criar_processo(client, csrf_de(PADRAO), caso["id"], seq=1)
        hist = client.get(f"/api/processos/{proc['id']}/historico").json()
        assert hist[0]["usuario_id"] == advogada.id

    def test_historico_respeita_escopo(
        self, client, csrf_de, advogada, criar_cliente
    ):
        cliente = criar_cliente(nome="Hist Alheio")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        proc = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        resp = client.get(
            f"/api/processos/{proc['id']}/historico",
            headers={CSRF: csrf_de(PADRAO)},
        )
        assert resp.status_code == 404

    def test_historico_nao_tem_escrita(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Hist Escrita")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        proc = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        csrf = csrf_de(ADMIN)
        resp = client.post(
            f"/api/processos/{proc['id']}/historico",
            headers={CSRF: csrf},
            json={"operacao": "FALSO", "dados": {}},
        )
        assert resp.status_code in (404, 405)  # sem endpoint de escrita

    def test_historico_preserva_registros_existentes(
        self, client, csrf_de, criar_cliente
    ):
        """Atualizacoes posteriores nao alteram entradas anteriores."""
        cliente = criar_cliente(nome="Hist Imutavel")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        proc = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        client.patch(
            f"/api/processos/{proc['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"tribunal": "TJSP"},
        )
        antes = client.get(f"/api/processos/{proc['id']}/historico").json()
        client.patch(
            f"/api/processos/{proc['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"tribunal": "TJRS"},
        )
        depois = client.get(f"/api/processos/{proc['id']}/historico").json()
        criacao_antes = [h for h in antes if h["operacao"] == "CRIACAO"][0]
        criacao_depois = [h for h in depois if h["operacao"] == "CRIACAO"][0]
        assert criacao_antes == criacao_depois  # entrada imutavel
        # historico ordenado do mais recente: a entrada antiga (None -> TJSP)
        # permanece intacta e a nova registra (TJSP -> TJRS)
        atualizacoes = [h for h in depois if h["operacao"] == "ATUALIZACAO"]
        assert len(atualizacoes) == 2
        assert atualizacoes[0]["dados"]["tribunal"] == {
            "antes": "TJSP",
            "depois": "TJRS",
        }
        assert atualizacoes[1]["dados"]["tribunal"] == {
            "antes": None,
            "depois": "TJSP",
        }


# ----------------------------------------------- integridade e dados legados


class TestIntegridadeELegado:
    def test_varios_processos_no_mesmo_caso_1_para_n(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="1:N")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        p1 = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=1)
        p2 = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=2)
        assert p1["caso_id"] == p2["caso_id"] == caso["id"]
        assert p1["id"] != p2["id"]
        itens = client.get(f"/api/casos/{caso['id']}/processos").json()
        assert len(itens) == 2

    def test_caso_sem_processos_e_processo_sem_caso_nao_existe(
        self, client, csrf_de, criar_cliente
    ):
        """Todo processo pertence a um caso: nao ha payload de caso avulso."""
        cliente = criar_cliente(nome="Sem Vinculo")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        # listagem do caso vazia (caso existe, 0 processos)
        assert client.get(f"/api/casos/{caso['id']}/processos").json() == []
        # payload de criacao GERAL nao existe - cadastro e so por caso
        resp = client.post(
            "/api/processos",
            headers={CSRF: csrf_de(ADMIN)},
            json={"numero_processo": _numero(1)},
        )
        assert resp.status_code in (404, 405)

    def test_criador_registrado_no_banco(
        self, client, csrf_de, criar_caso, db_session
    ):
        from app.models.processo_judicial import ProcessoJudicial

        caso = criar_caso()
        proc = _criar_processo(client, csrf_de(ADMIN), caso.id, seq=1)
        objeto = db_session.get(ProcessoJudicial, proc["id"])
        assert objeto is not None
        assert objeto.caso_id == caso.id
        assert objeto.criado_por is not None
        assert objeto.criador is not None  # relationship N:1 com Usuario
        assert objeto.caso.id == caso.id  # relationship N:1 com Caso

    def test_caso_legado_com_numero_preservado_apos_criar_processo(
        self, client, csrf_de, db_session
    ):
        """Criar processo NUNCA altera `Caso.numero_processo` (legado)."""
        from app.models.caso import Caso

        legado = Caso(cliente="Legado", numero_processo="1", area="Civel")
        db_session.add(legado)
        db_session.commit()
        db_session.refresh(legado)

        resp = client.post(
            f"/api/casos/{legado.id}/processos",
            headers={CSRF: csrf_de(ADMIN)},
            json={"numero_processo": _numero(1)},
        )
        assert resp.status_code == 201, resp.text

        db_session.refresh(legado)
        assert legado.numero_processo == "1"  # intocado
        # e o numero do processo e outro registro (entidade independente)
        assert resp.json()["numero_processo"] != "1"
        # o caso legado continua legivel pela API com o numero antigo
        detalhe = client.get(f"/api/casos/{legado.id}")
        assert detalhe.status_code == 200
        assert detalhe.json()["numero_processo"] == "1"

    def test_criar_caso_com_numero_nao_gera_processo_automatico(
        self, client, csrf_de, criar_cliente
    ):
        """Compatibilidade Fase 2: `CasoCreate` segue aceitando numero legado
        (sem validacao CNJ) e isso NAO cria ProcessoJudicial."""
        cliente = criar_cliente(nome="Legado Novo")
        resp = client.post(
            "/api/casos",
            headers={CSRF: csrf_de(ADMIN)},
            json={
                "titulo": "Caso com numero legado",
                "cliente_id": cliente.id,
                "numero_processo": "0001111-22.2026.8.26.0100",  # DD invalido
            },
        )
        assert resp.status_code == 201, resp.text
        caso_id = resp.json()["id"]
        assert resp.json()["numero_processo"] == "0001111-22.2026.8.26.0100"
        # nenhum processo judicial derivado
        assert client.get(f"/api/casos/{caso_id}/processos").json() == []
        assert client.get("/api/processos?limite=100").json()["total"] == 0

    def test_concessao_de_processos_propaga_na_api(
        self, client, csrf_de, funcionario, criar_caso
    ):
        """O admin concede `pode_gerenciar_processos` pela API (sem escalada)."""
        caso = criar_caso()
        resp = client.post(
            f"/api/casos/{caso.id}/usuarios",
            headers={CSRF: csrf_de(ADMIN)},
            json={
                "usuario_id": funcionario.id,
                "pode_visualizar": True,
                "pode_gerenciar_processos": True,
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["pode_gerenciar_processos"] is True

        # e o funcionario entao consegue cadastrar
        criar = client.post(
            f"/api/casos/{caso.id}/processos",
            headers={CSRF: csrf_de(FUNCIONARIO)},
            json={"numero_processo": _numero(1)},
        )
        assert criar.status_code == 201, criar.text
