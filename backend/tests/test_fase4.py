"""Testes da Fase 4: prazos e compromissos de agenda.

Cobrem as regras de negocio exigidas: prazo com caso obrigatorio e ativo,
processo opcional do MESMO caso, responsavel ativo com acesso, periodo
coerente (data_inicio <= data_vencimento), status inicial PENDENTE sem
escalada pelo payload, "vencido" sempre CALCULADO na data local de Brasilia,
urgentes (VENCIDO/HOJE/PROXIMO) com horizonte de no maximo 90 dias e
paginacao no banco; compromissos com permissao PROPRIA
(`pode_gerenciar_compromissos` - `pode_gerenciar_prazos` nao concede),
compromisso sem caso restrito ao administrador, status somente pela rota
`/status`, agenda com semantica de SOBREPOSICAO que nunca mistura prazos;
auditoria imutavel e ATOMICIDADE: negocio + auditoria na MESMA transacao
(falha na auditoria desfaz o negocio junto).
"""

from datetime import date, datetime, time, timedelta, timezone

import pytest

from app.core.tempo import hoje_brasilia
from tests.conftest import ADMIN, FUNCIONARIO, PADRAO, gerar_numero_cnj

CSRF = "X-CSRF-Token"


def _criar_caso_api(client, csrf, cliente_id, **dados):
    payload = {"titulo": "Caso da Fase 4", "cliente_id": cliente_id}
    payload.update(dados)
    resp = client.post("/api/casos", headers={CSRF: csrf}, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _criar_prazo(client, csrf, caso_id, **dados):
    """Cadastra um prazo (201) com vencimento padrao em +7 dias."""
    payload = {
        "caso_id": caso_id,
        "titulo": "Prazo da Fase 4",
        "data_vencimento": (hoje_brasilia() + timedelta(days=7)).isoformat(),
    }
    payload.update(dados)
    resp = client.post("/api/prazos", headers={CSRF: csrf}, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _criar_compromisso(client, csrf, **dados):
    """Cadastra um compromisso (201) padrao: amanha das 9h as 10h."""
    inicio = datetime.combine(
        hoje_brasilia() + timedelta(days=1), time(9, 0)
    )
    payload = {
        "titulo": "Compromisso da Fase 4",
        "tipo": "REUNIAO",
        "data_inicio": inicio.isoformat(),
        "data_fim": (inicio + timedelta(hours=1)).isoformat(),
    }
    payload.update(dados)
    resp = client.post("/api/compromissos", headers={CSRF: csrf}, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _criar_processo(client, csrf, caso_id, *, seq=1):
    resp = client.post(
        f"/api/casos/{caso_id}/processos",
        headers={CSRF: csrf},
        json={"numero_processo": gerar_numero_cnj(seq)},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _falha_de_auditoria(self, *args, **kwargs):
    """Simula falha no INSERT do historico (teste de atomicidade)."""
    raise RuntimeError("falha simulada na auditoria")


# --------------------------------------------------------------- prazos: CRUD


class TestCadastroPrazos:
    def test_cadastro_valido_201(self, client, csrf_de, criar_cliente, admin):
        cliente = criar_cliente(nome="Prazo Cadastro")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        resp = client.post(
            "/api/prazos",
            headers={CSRF: csrf_de(ADMIN)},
            json={
                "caso_id": caso["id"],
                "titulo": "Contestar sentenca",
                "descricao": "Prazo de 15 dias",
                "tipo": "PROCESSUAL",
                "data_inicio": hoje_brasilia().isoformat(),
                "data_vencimento": (hoje_brasilia() + timedelta(days=15)).isoformat(),
                "prioridade": "URGENTE",
                "observacoes": "Reunir documentos",
            },
        )
        assert resp.status_code == 201, resp.text
        corpo = resp.json()
        assert corpo["caso_id"] == caso["id"]
        assert corpo["titulo"] == "Contestar sentenca"
        assert corpo["status"] == "PENDENTE"  # status nasce PENDENTE
        assert corpo["vencido"] is False
        assert corpo["criado_por"] == admin.id
        assert corpo["concluido_em"] is None
        assert corpo["concluido_por"] is None
        # responsavel ausente = o proprio operador
        assert corpo["responsavel_id"] == admin.id

    def test_data_inicio_posterior_ao_vencimento_422(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="Periodo Ruim")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        resp = client.post(
            "/api/prazos",
            headers={CSRF: csrf_de(ADMIN)},
            json={
                "caso_id": caso["id"],
                "titulo": "Periodo invertido",
                "data_inicio": (hoje_brasilia() + timedelta(days=10)).isoformat(),
                "data_vencimento": hoje_brasilia().isoformat(),
            },
        )
        assert resp.status_code == 422, resp.text

    def test_caso_inexistente_404(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Caso Ruim")
        cliente.id  # so para criar o registro
        resp = client.post(
            "/api/prazos",
            headers={CSRF: csrf_de(ADMIN)},
            json={
                "caso_id": 99999,
                "titulo": "Prazo orfao",
                "data_vencimento": hoje_brasilia().isoformat(),
            },
        )
        assert resp.status_code == 404, resp.text

    def test_caso_arquivado_nao_recebe_prazo_422(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="Arquivado")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        arch = client.post(
            f"/api/casos/{caso['id']}/arquivar", headers={CSRF: csrf_de(ADMIN)}
        )
        assert arch.status_code == 200, arch.text
        resp = client.post(
            "/api/prazos",
            headers={CSRF: csrf_de(ADMIN)},
            json={
                "caso_id": caso["id"],
                "titulo": "Prazo de caso arquivado",
                "data_vencimento": hoje_brasilia().isoformat(),
            },
        )
        assert resp.status_code == 422, resp.text

    def test_usuario_sem_acesso_404(self, client, csrf_de, advogada, criar_cliente):
        cliente = criar_cliente(nome="Escopo")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        resp = client.post(
            "/api/prazos",
            headers={CSRF: csrf_de(PADRAO)},
            json={
                "caso_id": caso["id"],
                "titulo": "Fora do escopo",
                "data_vencimento": hoje_brasilia().isoformat(),
            },
        )
        assert resp.status_code == 404, resp.text

    def test_funcionario_com_acesso_sem_permissao_403(
        self, client, csrf_de, funcionario, criar_caso, conceder_acesso
    ):
        caso = criar_caso()
        conceder_acesso(caso, funcionario)  # so pode_visualizar
        resp = client.post(
            "/api/prazos",
            headers={CSRF: csrf_de(FUNCIONARIO)},
            json={
                "caso_id": caso.id,
                "titulo": "Sem grant de prazos",
                "data_vencimento": hoje_brasilia().isoformat(),
            },
        )
        assert resp.status_code == 403, resp.text

    def test_funcionario_com_grant_prazos_cadastra_201(
        self, client, csrf_de, funcionario, criar_caso, conceder_acesso
    ):
        caso = criar_caso()
        conceder_acesso(caso, funcionario, pode_gerenciar_prazos=True)
        resp = client.post(
            "/api/prazos",
            headers={CSRF: csrf_de(FUNCIONARIO)},
            json={
                "caso_id": caso.id,
                "titulo": "Com grant de prazos",
                "data_vencimento": hoje_brasilia().isoformat(),
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["criado_por"] == funcionario.id

    def test_responsavel_do_caso_cadastra_201(
        self, client, csrf_de, advogada, criar_cliente
    ):
        cliente = criar_cliente(nome="Resp")
        caso = _criar_caso_api(
            client, csrf_de(ADMIN), cliente.id, responsavel_id=advogada.id
        )
        resp = client.post(
            "/api/prazos",
            headers={CSRF: csrf_de(PADRAO)},
            json={
                "caso_id": caso["id"],
                "titulo": "Prazo da responsavel",
                "data_vencimento": hoje_brasilia().isoformat(),
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["responsavel_id"] == advogada.id

    def test_responsavel_inativo_422(self, client, csrf_de, criar_cliente, db_session):
        from app.core.security import hash_senha
        from app.models.usuario import Usuario

        cliente = criar_cliente(nome="Inativo")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        inativo = Usuario(
            nome="Inativo",
            email="inativo@jadilson.adv",
            senha_hash=hash_senha("Inativo@123"),
            perfil="FUNCIONARIO",
            ativo=False,
        )
        db_session.add(inativo)
        db_session.commit()
        resp = client.post(
            "/api/prazos",
            headers={CSRF: csrf_de(ADMIN)},
            json={
                "caso_id": caso["id"],
                "titulo": "Responsavel inativo",
                "data_vencimento": hoje_brasilia().isoformat(),
                "responsavel_id": inativo.id,
            },
        )
        assert resp.status_code == 422, resp.text

    def test_responsavel_sem_acesso_ao_caso_422(
        self, client, csrf_de, advogada, criar_cliente
    ):
        cliente = criar_cliente(nome="Sem Acesso")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        resp = client.post(
            "/api/prazos",
            headers={CSRF: csrf_de(ADMIN)},
            json={
                "caso_id": caso["id"],
                "titulo": "Responsavel sem grant",
                "data_vencimento": hoje_brasilia().isoformat(),
                "responsavel_id": advogada.id,
            },
        )
        assert resp.status_code == 422, resp.text

    def test_payload_nao_aceita_campos_de_auditoria(
        self, client, csrf_de, criar_cliente
    ):
        """extra=forbid: sem escalada de status nem falsificacao de auditoria."""
        cliente = criar_cliente(nome="Payload")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        csrf = csrf_de(ADMIN)
        for proibido in (
            {"status": "CONCLUIDO"},
            {"criado_por": 999},
            {"concluido_em": "2026-01-01T00:00:00"},
            {"concluido_por": 1},
            {"id": 1},
            {"vencido": True},
        ):
            payload = {
                "caso_id": caso["id"],
                "titulo": "Payload proibido",
                "data_vencimento": hoje_brasilia().isoformat(),
                **proibido,
            }
            resp = client.post(
                "/api/prazos", headers={CSRF: csrf}, json=payload
            )
            assert resp.status_code == 422, (proibido, resp.text)

    def test_sem_sessao_401(self, client, criar_cliente):
        resp = client.post(
            "/api/prazos",
            json={"caso_id": 1, "titulo": "Sem sessao",
                  "data_vencimento": hoje_brasilia().isoformat()},
        )
        assert resp.status_code == 401

    def test_sem_csrf_403(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="CSRF")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        resp = client.post(
            "/api/prazos",
            json={"caso_id": caso["id"], "titulo": "Sem CSRF",
                  "data_vencimento": hoje_brasilia().isoformat()},
        )
        assert resp.status_code == 403


# ------------------------------------------------------- prazos: consulta/filtros


class TestConsultaEPaginacaoPrazos:
    def test_detalhe_200_e_fora_do_escopo_404(
        self, client, csrf_de, advogada, criar_cliente
    ):
        cliente = criar_cliente(nome="Detalhe")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        prazo = _criar_prazo(client, csrf_de(ADMIN), caso["id"])

        resp = client.get(f"/api/prazos/{prazo['id']}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["id"] == prazo["id"]

        # advogada sem grant: mesmo codigo do 404 (nao vaza caso alheio)
        csrf_de(PADRAO)
        assert client.get(f"/api/prazos/{prazo['id']}").status_code == 404

    def test_detalhe_inexistente_404(self, client, csrf_de):
        csrf_de(ADMIN)
        assert client.get("/api/prazos/99999").status_code == 404

    def test_listagem_com_filtros(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Filtros")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        csrf = csrf_de(ADMIN)
        _criar_prazo(
            client, csrf, caso["id"], titulo="Recurso especial",
            tipo="PROCESSUAL", prioridade="URGENTE",
            data_vencimento=(hoje_brasilia() + timedelta(days=2)).isoformat(),
        )
        _criar_prazo(
            client, csrf, caso["id"], titulo="Prazo administrativo",
            tipo="ADMINISTRATIVO", prioridade="BAIXA",
            data_vencimento=(hoje_brasilia() + timedelta(days=30)).isoformat(),
        )

        def busca(params):
            resp = client.get(f"/api/prazos?{params}&limite=100")
            assert resp.status_code == 200, resp.text
            return {i["titulo"] for i in resp.json()["itens"]}

        assert busca("tipo=PROCESSUAL") == {"Recurso especial"}
        assert busca("tipo=ADMINISTRATIVO") == {"Prazo administrativo"}
        assert busca("prioridade=URGENTE") == {"Recurso especial"}
        assert busca("q=Recurso") == {"Recurso especial"}
        assert busca(f"caso_id={caso['id']}") == {
            "Recurso especial", "Prazo administrativo"
        }
        assert busca(
            f"vencimento_ate={(hoje_brasilia() + timedelta(days=7)).isoformat()}"
        ) == {"Recurso especial"}
        assert busca(
            f"vencimento_de={(hoje_brasilia() + timedelta(days=10)).isoformat()}"
        ) == {"Prazo administrativo"}

    def test_filtro_pendentes_significa_em_aberto(
        self, client, csrf_de, criar_cliente
    ):
        """`pendentes=true` = PENDENTE + EM_ANDAMENTO (nao so status PENDENTE)."""
        cliente = criar_cliente(nome="Pendentes")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        csrf = csrf_de(ADMIN)
        p1 = _criar_prazo(client, csrf, caso["id"], titulo="Pendente um")
        p2 = _criar_prazo(client, csrf, caso["id"], titulo="Pendente dois")
        p3 = _criar_prazo(client, csrf, caso["id"], titulo="Em andamento")
        # p3 vira EM_ANDAMENTO; p2 e concluido
        r = client.patch(
            f"/api/prazos/{p3['id']}",
            headers={CSRF: csrf},
            json={"status": "EM_ANDAMENTO"},
        )
        assert r.status_code == 200, r.text
        r = client.patch(
            f"/api/prazos/{p2['id']}/concluir", headers={CSRF: csrf}
        )
        assert r.status_code == 200, r.text

        abertos = client.get("/api/prazos?pendentes=true&limite=100")
        assert abertos.status_code == 200, abertos.text
        ids_abertos = {i["id"] for i in abertos.json()["itens"]}
        assert ids_abertos == {p1["id"], p3["id"]}

        fechados = client.get("/api/prazos?pendentes=false&limite=100")
        ids_fechados = {i["id"] for i in fechados.json()["itens"]}
        assert ids_fechados == {p2["id"]}

    def test_paginacao_no_banco(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Paginacao")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        csrf = csrf_de(ADMIN)
        for n in range(3):
            _criar_prazo(
                client, csrf, caso["id"], titulo=f"Prazo numero {n}",
                data_vencimento=(hoje_brasilia() + timedelta(days=n + 1)).isoformat(),
            )

        p1 = client.get("/api/prazos?pagina=1&limite=2")
        corpo1 = p1.json()
        assert corpo1["total"] == 3
        assert len(corpo1["itens"]) == 2

        p2 = client.get("/api/prazos?pagina=2&limite=2")
        corpo2 = p2.json()
        assert corpo2["total"] == 3
        assert len(corpo2["itens"]) == 1
        ids1 = {i["id"] for i in corpo1["itens"]}
        ids2 = {i["id"] for i in corpo2["itens"]}
        assert not ids1 & ids2  # paginas disjuntas

    def test_listagem_respeita_escopo(
        self, client, csrf_de, advogada, criar_caso, conceder_acesso
    ):
        meu = criar_caso(cliente="Meu")
        alheio = criar_caso(cliente="Alheio")
        sem_grant = criar_caso(cliente="Sem grant")
        conceder_acesso(meu, advogada)
        csrf = csrf_de(ADMIN)
        _criar_prazo(client, csrf, meu.id, titulo="Do meu caso")
        _criar_prazo(client, csrf, alheio.id, titulo="Do caso alheio")
        _criar_prazo(client, csrf, sem_grant.id, titulo="Do caso sem grant")

        csrf_de(PADRAO)
        resp = client.get("/api/prazos?limite=100")
        assert resp.status_code == 200, resp.text
        titulos = {i["titulo"] for i in resp.json()["itens"]}
        assert titulos == {"Do meu caso"}
        # tentativa de contorno pelo filtro de caso alheio
        fuga = client.get(f"/api/prazos?caso_id={sem_grant.id}")
        assert fuga.json()["total"] == 0


# ------------------------------------------------------------ prazos: urgentes


class TestPrazosUrgentes:
    def _montar_massa(self, client, csrf, caso_id):
        """Vencido + hoje + proximo + um concluido vencido (que fica de fora)."""
        vencido = _criar_prazo(
            client, csrf, caso_id, titulo="Ja venceu",
            data_vencimento=(hoje_brasilia() - timedelta(days=3)).isoformat(),
        )
        hoje = _criar_prazo(
            client, csrf, caso_id, titulo="Vence hoje",
            data_vencimento=hoje_brasilia().isoformat(),
        )
        proximo = _criar_prazo(
            client, csrf, caso_id, titulo="Proximo",
            data_vencimento=(hoje_brasilia() + timedelta(days=5)).isoformat(),
        )
        longe = _criar_prazo(
            client, csrf, caso_id, titulo="Fora do horizonte",
            data_vencimento=(hoje_brasilia() + timedelta(days=40)).isoformat(),
        )
        concluido = _criar_prazo(
            client, csrf, caso_id, titulo="Concluido vencido",
            data_vencimento=(hoje_brasilia() - timedelta(days=2)).isoformat(),
        )
        r = client.patch(
            f"/api/prazos/{concluido['id']}/concluir", headers={CSRF: csrf}
        )
        assert r.status_code == 200, r.text
        return vencido, hoje, proximo, longe, concluido

    def test_classificacao_vencido_hoje_proximo(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="Urgentes")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        csrf = csrf_de(ADMIN)
        vencido, hoje, proximo, longe, concluido = self._montar_massa(
            client, csrf, caso["id"]
        )

        resp = client.get("/api/prazos/urgentes?dias=7&limite=100")
        assert resp.status_code == 200, resp.text
        corpo = resp.json()
        por_titulo = {i["titulo"]: i for i in corpo["itens"]}

        assert por_titulo["Ja venceu"]["situacao"] == "VENCIDO"
        assert por_titulo["Ja venceu"]["vencido"] is True
        assert por_titulo["Vence hoje"]["situacao"] == "HOJE"
        assert por_titulo["Vence hoje"]["vencido"] is False
        assert por_titulo["Proximo"]["situacao"] == "PROXIMO"
        # fora do horizonte e concluidos ficam de fora
        assert "Fora do horizonte" not in por_titulo
        assert "Concluido vencido" not in por_titulo
        assert corpo["total"] == 3
        assert corpo["dias"] == 7
        # ordenacao: VENCIDO -> HOJE -> PROXIMO
        situacoes = [i["situacao"] for i in corpo["itens"]]
        assert situacoes == ["VENCIDO", "HOJE", "PROXIMO"]

    def test_urgentes_mantem_caso_numero_e_cliente(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="Campos Extras")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        _criar_prazo(
            client, csrf_de(ADMIN), caso["id"],
            data_vencimento=(hoje_brasilia() - timedelta(days=1)).isoformat(),
        )
        resp = client.get("/api/prazos/urgentes?dias=0")
        assert resp.status_code == 200, resp.text
        item = resp.json()["itens"][0]
        assert item["numero_processo"] == caso["numero_processo"]
        assert item["cliente"] == caso["cliente"]

    def test_horizonte_maximo_90_dias(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Horizonte")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        resp = client.get("/api/prazos/urgentes?dias=91")
        assert resp.status_code == 422, resp.text
        ok = client.get("/api/prazos/urgentes?dias=90")
        assert ok.status_code == 200, ok.text

    def test_urgentes_somente_em_aberto(self, client, csrf_de, criar_cliente):
        """Cancelados tambem ficam de fora (nao so concluidos)."""
        cliente = criar_cliente(nome="Cancelado")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        csrf = csrf_de(ADMIN)
        cancelado = _criar_prazo(
            client, csrf, caso["id"],
            data_vencimento=(hoje_brasilia() - timedelta(days=4)).isoformat(),
        )
        r = client.patch(
            f"/api/prazos/{cancelado['id']}/cancelar", headers={CSRF: csrf}
        )
        assert r.status_code == 200, r.text
        resp = client.get("/api/prazos/urgentes?dias=7")
        assert resp.status_code == 200, resp.text
        assert resp.json()["total"] == 0

    def test_urgentes_respeitam_escopo(
        self, client, csrf_de, advogada, criar_caso, conceder_acesso
    ):
        meu = criar_caso(cliente="Meu urgente")
        alheio = criar_caso(cliente="Alheio urgente")
        conceder_acesso(meu, advogada)
        csrf = csrf_de(ADMIN)
        _criar_prazo(
            client, csrf, meu.id,
            data_vencimento=(hoje_brasilia() - timedelta(days=1)).isoformat(),
        )
        _criar_prazo(
            client, csrf, alheio.id,
            data_vencimento=(hoje_brasilia() - timedelta(days=1)).isoformat(),
        )
        csrf_de(PADRAO)
        resp = client.get("/api/prazos/urgentes?dias=7")
        assert resp.status_code == 200, resp.text
        assert resp.json()["total"] == 1

    def test_urgentes_paginacao_no_banco(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="Pagina urgente")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        csrf = csrf_de(ADMIN)
        for n in range(3):
            _criar_prazo(
                client, csrf, caso["id"], titulo=f"Urgente {n}",
                data_vencimento=(hoje_brasilia() - timedelta(days=n + 1)).isoformat(),
            )
        p1 = client.get("/api/prazos/urgentes?dias=7&pagina=1&limite=2")
        assert p1.json()["total"] == 3
        assert len(p1.json()["itens"]) == 2
        p2 = client.get("/api/prazos/urgentes?dias=7&pagina=2&limite=2")
        assert len(p2.json()["itens"]) == 1
        ids1 = {i["id"] for i in p1.json()["itens"]}
        ids2 = {i["id"] for i in p2.json()["itens"]}
        assert not ids1 & ids2


# --------------------------------------------------- prazos: PATCH e transicoes


class TestEdicaoPrazo:
    def test_atualizacao_parcial_200(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Edita")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        prazo = _criar_prazo(client, csrf_de(ADMIN), caso["id"])
        resp = client.patch(
            f"/api/prazos/{prazo['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"titulo": "Titulo revisado", "prioridade": "ALTA"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["titulo"] == "Titulo revisado"
        assert resp.json()["prioridade"] == "ALTA"

    def test_payload_nao_aceita_caso_id_ni_status_final(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="Patch Proibido")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        outro = _criar_caso_api(client, csrf_de(ADMIN), cliente.id, titulo="Outro")
        prazo = _criar_prazo(client, csrf_de(ADMIN), caso["id"])
        csrf = csrf_de(ADMIN)
        for proibido in (
            {"caso_id": outro["id"]},
            {"criado_por": 999},
            {"concluido_em": "2026-01-01T00:00:00"},
            {"id": 1},
        ):
            resp = client.patch(
                f"/api/prazos/{prazo['id']}", headers={CSRF: csrf},
                json=proibido,
            )
            assert resp.status_code == 422, (proibido, resp.text)
        # status final so pelas rotas proprias
        resp = client.patch(
            f"/api/prazos/{prazo['id']}", headers={CSRF: csrf},
            json={"status": "CONCLUIDO"},
        )
        assert resp.status_code == 422, resp.text
        # e o caso nao mudou
        detalhe = client.get(f"/api/prazos/{prazo['id']}")
        assert detalhe.json()["caso_id"] == caso["id"]

    def test_data_inicio_mais_recente_que_vencimento_422(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="Periodo Patch")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        prazo = _criar_prazo(
            client, csrf_de(ADMIN), caso["id"],
            data_vencimento=(hoje_brasilia() + timedelta(days=5)).isoformat(),
        )
        resp = client.patch(
            f"/api/prazos/{prazo['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"data_inicio": (hoje_brasilia() + timedelta(days=10)).isoformat()},
        )
        assert resp.status_code == 422, resp.text

    def test_prazo_concluido_nao_edita_409(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Concluido Edit")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        csrf = csrf_de(ADMIN)
        prazo = _criar_prazo(client, csrf, caso["id"])
        r = client.patch(f"/api/prazos/{prazo['id']}/concluir", headers={CSRF: csrf})
        assert r.status_code == 200, r.text
        resp = client.patch(
            f"/api/prazos/{prazo['id']}", headers={CSRF: csrf},
            json={"titulo": "Nao deveria alterar"},
        )
        assert resp.status_code == 409, resp.text

    def test_prazo_de_caso_alheio_404_no_patch(
        self, client, csrf_de, advogada, criar_cliente
    ):
        cliente = criar_cliente(nome="Alheio Patch")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        prazo = _criar_prazo(client, csrf_de(ADMIN), caso["id"])
        resp = client.patch(
            f"/api/prazos/{prazo['id']}",
            headers={CSRF: csrf_de(PADRAO)},
            json={"titulo": "Invadindo"},
        )
        assert resp.status_code == 404, resp.text


class TestTransicoesPrazo:
    def test_concluir_registra_data_hora_e_usuario(
        self, client, csrf_de, criar_cliente, admin
    ):
        cliente = criar_cliente(nome="Concluir")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        prazo = _criar_prazo(client, csrf_de(ADMIN), caso["id"])
        resp = client.patch(
            f"/api/prazos/{prazo['id']}/concluir", headers={CSRF: csrf_de(ADMIN)}
        )
        assert resp.status_code == 200, resp.text
        corpo = resp.json()
        assert corpo["status"] == "CONCLUIDO"
        assert corpo["concluido_em"] is not None
        assert corpo["concluido_por"] == admin.id
        assert corpo["vencido"] is False  # concluido nunca aparece vencido

    def test_concluir_de_novo_409(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Duplo concluir")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        csrf = csrf_de(ADMIN)
        prazo = _criar_prazo(client, csrf, caso["id"])
        assert (
            client.patch(
                f"/api/prazos/{prazo['id']}/concluir", headers={CSRF: csrf}
            ).status_code
            == 200
        )
        resp = client.patch(
            f"/api/prazos/{prazo['id']}/concluir", headers={CSRF: csrf}
        )
        assert resp.status_code == 409, resp.text

    def test_cancelar_prazo_em_aberto_200(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Cancelar")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        prazo = _criar_prazo(client, csrf_de(ADMIN), caso["id"])
        resp = client.patch(
            f"/api/prazos/{prazo['id']}/cancelar", headers={CSRF: csrf_de(ADMIN)}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "CANCELADO"

    def test_concluir_prazo_cancelado_409(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Cancelado concluir")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        csrf = csrf_de(ADMIN)
        prazo = _criar_prazo(client, csrf, caso["id"])
        client.patch(f"/api/prazos/{prazo['id']}/cancelar", headers={CSRF: csrf})
        resp = client.patch(
            f"/api/prazos/{prazo['id']}/concluir", headers={CSRF: csrf}
        )
        assert resp.status_code == 409, resp.text

    def test_reabrir_preserva_historico_e_limpa_conclusao(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="Reabrir")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        csrf = csrf_de(ADMIN)
        prazo = _criar_prazo(client, csrf, caso["id"])
        client.patch(f"/api/prazos/{prazo['id']}/concluir", headers={CSRF: csrf})
        antes = client.get(f"/api/prazos/{prazo['id']}/historico").json()
        assert [h["operacao"] for h in antes] == ["CONCLUSAO", "CRIACAO"]

        resp = client.patch(
            f"/api/prazos/{prazo['id']}/reabrir", headers={CSRF: csrf}
        )
        assert resp.status_code == 200, resp.text
        corpo = resp.json()
        assert corpo["status"] == "PENDENTE"
        assert corpo["concluido_em"] is None
        assert corpo["concluido_por"] is None

        depois = client.get(f"/api/prazos/{prazo['id']}/historico").json()
        # historico integral: reabertura nova + registros anteriores intactos
        assert [h["operacao"] for h in depois] == [
            "REABERTURA", "CONCLUSAO", "CRIACAO",
        ]

    def test_reabrir_prazo_aberto_409(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Reabrir aberto")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        prazo = _criar_prazo(client, csrf_de(ADMIN), caso["id"])
        resp = client.patch(
            f"/api/prazos/{prazo['id']}/reabrir", headers={CSRF: csrf_de(ADMIN)}
        )
        assert resp.status_code == 409, resp.text

    def test_transicoes_fora_de_escopo_404(
        self, client, csrf_de, advogada, criar_cliente
    ):
        cliente = criar_cliente(nome="Transicao alheia")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        prazo = _criar_prazo(client, csrf_de(ADMIN), caso["id"])
        csrf_de(PADRAO)
        for rota in ("concluir", "reabrir", "cancelar"):
            resp = client.patch(
                f"/api/prazos/{prazo['id']}/{rota}", headers={CSRF: csrf_de(PADRAO)}
            )
            assert resp.status_code == 404, rota


# ------------------------------------------------- prazos: auditoria e atomicidade


class TestHistoricoPrazo:
    def test_criacao_gera_registro(self, client, csrf_de, criar_cliente, admin):
        cliente = criar_cliente(nome="Hist")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        prazo = _criar_prazo(client, csrf_de(ADMIN), caso["id"])
        hist = client.get(f"/api/prazos/{prazo['id']}/historico")
        assert hist.status_code == 200, hist.text
        assert [h["operacao"] for h in hist.json()] == ["CRIACAO"]
        assert hist.json()[0]["usuario_id"] == admin.id

    def test_atualizacao_registra_antes_depois(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="Hist Update")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        prazo = _criar_prazo(client, csrf_de(ADMIN), caso["id"])
        client.patch(
            f"/api/prazos/{prazo['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"titulo": "Novo titulo"},
        )
        hist = client.get(f"/api/prazos/{prazo['id']}/historico").json()
        atualizacao = [h for h in hist if h["operacao"] == "ATUALIZACAO"]
        assert len(atualizacao) == 1
        assert atualizacao[0]["dados"]["titulo"] == {
            "antes": "Prazo da Fase 4",
            "depois": "Novo titulo",
        }

    def test_mudanca_de_vencimento_e_responsavel_entradas_proprias(
        self, client, csrf_de, advogada, criar_cliente
    ):
        cliente = criar_cliente(nome="Mudancas")
        caso = _criar_caso_api(
            client, csrf_de(ADMIN), cliente.id, responsavel_id=advogada.id
        )
        # a criacao do caso ja gera a linha de acesso da advogada responsavel
        # (mesma regra da Fase 1) - ela pode assumir o prazo sem grant extra
        prazo = _criar_prazo(client, csrf_de(ADMIN), caso["id"])
        novo_venc = (hoje_brasilia() + timedelta(days=20)).isoformat()
        resp = client.patch(
            f"/api/prazos/{prazo['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"data_vencimento": novo_venc},
        )
        assert resp.status_code == 200, resp.text
        # troca o responsavel para o proprio advogada (grant ativo)
        resp = client.patch(
            f"/api/prazos/{prazo['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"responsavel_id": advogada.id},
        )
        assert resp.status_code == 200, resp.text

        hist = client.get(f"/api/prazos/{prazo['id']}/historico").json()
        mudanca_venc = [h for h in hist if h["operacao"] == "MUDANCA_VENCIMENTO"]
        assert len(mudanca_venc) == 1
        assert mudanca_venc[0]["dados"]["data_vencimento"]["depois"] == novo_venc
        mudanca_resp = [
            h for h in hist if h["operacao"] == "MUDANCA_RESPONSAVEL"
        ]
        assert len(mudanca_resp) == 1
        assert mudanca_resp[0]["dados"]["responsavel_id"]["depois"] == advogada.id

    def test_conclusao_e_reabertura_registradas(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="Hist fim")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        csrf = csrf_de(ADMIN)
        prazo = _criar_prazo(client, csrf, caso["id"])
        client.patch(f"/api/prazos/{prazo['id']}/concluir", headers={CSRF: csrf})
        client.patch(f"/api/prazos/{prazo['id']}/reabrir", headers={CSRF: csrf})
        client.patch(f"/api/prazos/{prazo['id']}/cancelar", headers={CSRF: csrf})
        hist = client.get(f"/api/prazos/{prazo['id']}/historico").json()
        assert [h["operacao"] for h in hist] == [
            "CANCELAMENTO", "REABERTURA", "CONCLUSAO", "CRIACAO",
        ]
        conclusao = [h for h in hist if h["operacao"] == "CONCLUSAO"][0]
        assert conclusao["dados"]["status"]["antes"] == "PENDENTE"
        assert conclusao["dados"]["status"]["depois"] == "CONCLUIDO"

    def test_atualizacao_identica_nao_grava(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="Igual")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        prazo = _criar_prazo(client, csrf_de(ADMIN), caso["id"], titulo="Fixo")
        resp = client.patch(
            f"/api/prazos/{prazo['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"titulo": "Fixo"},
        )
        assert resp.status_code == 200, resp.text
        hist = client.get(f"/api/prazos/{prazo['id']}/historico").json()
        assert [h["operacao"] for h in hist] == ["CRIACAO"]

    def test_historico_respeita_escopo_e_nao_tem_escrita(
        self, client, csrf_de, advogada, criar_cliente
    ):
        cliente = criar_cliente(nome="Hist escopo")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        prazo = _criar_prazo(client, csrf_de(ADMIN), caso["id"])

        csrf_de(PADRAO)
        resp = client.get(f"/api/prazos/{prazo['id']}/historico")
        assert resp.status_code == 404, resp.text

        # sem endpoint de escrita no historico
        escrita = client.post(
            f"/api/prazos/{prazo['id']}/historico",
            headers={CSRF: csrf_de(ADMIN)},
            json={"operacao": "FALSO", "dados": {}},
        )
        assert escrita.status_code in (404, 405)


class TestAtomicidadePrazo:
    """Negocio + auditoria compartilham UMA transacao (rollback total)."""

    def test_falha_na_auditoria_desfaz_a_criacao(
        self, client, csrf_de, criar_cliente, db_session, monkeypatch
    ):
        from app.models.prazo import Prazo
        from app.repositories.prazo_historico_repository import (
            PrazoHistoricoRepository,
        )

        cliente = criar_cliente(nome="Atomico")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        monkeypatch.setattr(
            PrazoHistoricoRepository, "registrar", _falha_de_auditoria
        )
        with pytest.raises(RuntimeError, match="auditoria"):
            client.post(
                "/api/prazos",
                headers={CSRF: csrf_de(ADMIN)},
                json={
                    "caso_id": caso["id"],
                    "titulo": "Nao pode persistir",
                    "data_vencimento": hoje_brasilia().isoformat(),
                },
            )
        db_session.expire_all()
        persistido = (
            db_session.query(Prazo)
            .filter(Prazo.titulo == "Nao pode persistir")
            .count()
        )
        assert persistido == 0, "prazo criado sem a sua auditoria"

    def test_falha_na_auditoria_desfaz_a_edicao(
        self, client, csrf_de, criar_cliente, db_session, monkeypatch
    ):
        from app.models.prazo import Prazo
        from app.repositories.prazo_historico_repository import (
            PrazoHistoricoRepository,
        )

        cliente = criar_cliente(nome="Atomico edit")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        prazo = _criar_prazo(client, csrf_de(ADMIN), caso["id"])

        monkeypatch.setattr(
            PrazoHistoricoRepository, "registrar", _falha_de_auditoria
        )
        with pytest.raises(RuntimeError, match="auditoria"):
            client.patch(
                f"/api/prazos/{prazo['id']}",
                headers={CSRF: csrf_de(ADMIN)},
                json={"titulo": "Alteracao invalida"},
            )
        db_session.expire_all()
        objeto = db_session.get(Prazo, prazo["id"])
        assert objeto.titulo == "Prazo da Fase 4", "edicao persistiu sem auditoria"

    def test_falha_na_auditoria_desfaz_a_conclusao(
        self, client, csrf_de, criar_cliente, db_session, monkeypatch
    ):
        from app.models.prazo import Prazo
        from app.repositories.prazo_historico_repository import (
            PrazoHistoricoRepository,
        )

        cliente = criar_cliente(nome="Atomico conclui")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        prazo = _criar_prazo(client, csrf_de(ADMIN), caso["id"])

        monkeypatch.setattr(
            PrazoHistoricoRepository, "registrar", _falha_de_auditoria
        )
        with pytest.raises(RuntimeError, match="auditoria"):
            client.patch(
                f"/api/prazos/{prazo['id']}/concluir",
                headers={CSRF: csrf_de(ADMIN)},
            )
        db_session.expire_all()
        objeto = db_session.get(Prazo, prazo["id"])
        assert objeto.status == "PENDENTE"
        assert objeto.concluido_em is None
        assert objeto.concluido_por is None


# ----------------------------------------------------------- compromissos: CRUD


class TestCadastroCompromissos:
    def test_cadastro_com_caso_201(self, client, csrf_de, criar_cliente, admin):
        cliente = criar_cliente(nome="Compromisso")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        resp = client.post(
            "/api/compromissos",
            headers={CSRF: csrf_de(ADMIN)},
            json={
                "caso_id": caso["id"],
                "titulo": "Audiencia inicial",
                "descricao": "Vara civil",
                "tipo": "AUDIENCIA",
                "data_inicio": "2026-12-10T09:00:00",
                "data_fim": "2026-12-10T11:00:00",
                "local": "Foro Central",
            },
        )
        assert resp.status_code == 201, resp.text
        corpo = resp.json()
        assert corpo["caso_id"] == caso["id"]
        assert corpo["status"] == "AGENDADO"
        assert corpo["tipo"] == "AUDIENCIA"
        assert corpo["criado_por"] == admin.id
        assert corpo["data_inicio"] == "2026-12-10T09:00:00"
        assert corpo["data_fim"] == "2026-12-10T11:00:00"

    def test_cadastro_sem_caso_somente_admin(
        self, client, csrf_de, advogada, funcionario
    ):
        """Agenda pessoal do escritorio: sem caso, so o administrador."""
        payload = {
            "titulo": "Consulta particular",
            "tipo": "ATENDIMENTO",
            "data_inicio": "2026-12-11T14:00:00",
            "data_fim": "2026-12-11T15:00:00",
        }
        resp = client.post(
            "/api/compromissos", headers={CSRF: csrf_de(ADMIN)}, json=payload
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["caso_id"] is None

        resp = client.post(
            "/api/compromissos", headers={CSRF: csrf_de(PADRAO)}, json=payload
        )
        assert resp.status_code == 403, resp.text

        resp = client.post(
            "/api/compromissos", headers={CSRF: csrf_de(FUNCIONARIO)}, json=payload
        )
        assert resp.status_code == 403, resp.text

    def test_data_fim_igual_ou_anterior_422(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Periodo comp")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        resp = client.post(
            "/api/compromissos",
            headers={CSRF: csrf_de(ADMIN)},
            json={
                "caso_id": caso["id"],
                "titulo": "Periodo invalido",
                "tipo": "REUNIAO",
                "data_inicio": "2026-12-10T10:00:00",
                "data_fim": "2026-12-10T10:00:00",
            },
        )
        assert resp.status_code == 422, resp.text

    def test_processo_de_outro_caso_422(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Processo comp")
        caso_a = _criar_caso_api(client, csrf_de(ADMIN), cliente.id, titulo="Caso A")
        caso_b = _criar_caso_api(client, csrf_de(ADMIN), cliente.id, titulo="Caso B")
        proc_a = _criar_processo(client, csrf_de(ADMIN), caso_a["id"], seq=1)
        resp = client.post(
            "/api/compromissos",
            headers={CSRF: csrf_de(ADMIN)},
            json={
                "caso_id": caso_b["id"],
                "processo_id": proc_a["id"],
                "titulo": "Processo alheio",
                "tipo": "AUDIENCIA",
                "data_inicio": "2026-12-10T09:00:00",
                "data_fim": "2026-12-10T10:00:00",
            },
        )
        assert resp.status_code == 422, resp.text

    def test_processo_do_mesmo_caso_201(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="Processo ok")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        proc = _criar_processo(client, csrf_de(ADMIN), caso["id"], seq=2)
        resp = client.post(
            "/api/compromissos",
            headers={CSRF: csrf_de(ADMIN)},
            json={
                "caso_id": caso["id"],
                "processo_id": proc["id"],
                "titulo": "Diligencia no processo",
                "tipo": "DILIGENCIA",
                "data_inicio": "2026-12-10T09:00:00",
                "data_fim": "2026-12-10T10:00:00",
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["processo_id"] == proc["id"]

    def test_payload_nao_aceita_status_nem_caso_id_no_patch(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="Payload comp")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        csrf = csrf_de(ADMIN)
        # POST: status nasce AGENDADO, sem escalada pelo payload
        resp = client.post(
            "/api/compromissos",
            headers={CSRF: csrf},
            json={
                "caso_id": caso["id"],
                "titulo": "Sem status",
                "tipo": "REUNIAO",
                "data_inicio": "2026-12-10T09:00:00",
                "data_fim": "2026-12-10T10:00:00",
                "status": "REALIZADO",
                "criado_por": 999,
            },
        )
        assert resp.status_code == 422, resp.text

        comp = _criar_compromisso(client, csrf, caso_id=caso["id"])
        for proibido in (
            {"caso_id": 9999},
            {"processo_id": 1},
            {"status": "CANCELADO"},
            {"criado_por": 999},
            {"id": 1},
        ):
            r = client.patch(
                f"/api/compromissos/{comp['id']}", headers={CSRF: csrf},
                json=proibido,
            )
            assert r.status_code == 422, (proibido, r.text)

    def test_caso_arquivado_nao_recebe_compromisso_422(
        self, client, csrf_de, criar_cliente
    ):
        cliente = criar_cliente(nome="Comp arch")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        client.post(f"/api/casos/{caso['id']}/arquivar", headers={CSRF: csrf_de(ADMIN)})
        resp = client.post(
            "/api/compromissos",
            headers={CSRF: csrf_de(ADMIN)},
            json={
                "caso_id": caso["id"],
                "titulo": "Compromisso arquivado",
                "tipo": "REUNIAO",
                "data_inicio": "2026-12-10T09:00:00",
                "data_fim": "2026-12-10T10:00:00",
            },
        )
        assert resp.status_code == 422, resp.text

    def test_responsavel_inativo_422(self, client, csrf_de, criar_cliente, db_session):
        from app.core.security import hash_senha
        from app.models.usuario import Usuario

        cliente = criar_cliente(nome="Comp inativo")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        inativo = Usuario(
            nome="Inativo Comp",
            email="inativo.comp@jadilson.adv",
            senha_hash=hash_senha("Inativo@123"),
            perfil="FUNCIONARIO",
            ativo=False,
        )
        db_session.add(inativo)
        db_session.commit()
        resp = client.post(
            "/api/compromissos",
            headers={CSRF: csrf_de(ADMIN)},
            json={
                "caso_id": caso["id"],
                "titulo": "Responsavel inativo",
                "tipo": "REUNIAO",
                "data_inicio": "2026-12-10T09:00:00",
                "data_fim": "2026-12-10T10:00:00",
                "responsavel_id": inativo.id,
            },
        )
        assert resp.status_code == 422, resp.text

    def test_sem_sessao_401(self, client):
        resp = client.post(
            "/api/compromissos",
            json={"titulo": "Sem sessao", "tipo": "REUNIAO",
                  "data_inicio": "2026-12-10T09:00:00",
                  "data_fim": "2026-12-10T10:00:00"},
        )
        assert resp.status_code == 401

    def test_sem_csrf_403(self, client, csrf_de, criar_cliente):
        cliente = criar_cliente(nome="CSRF comp")
        caso = _criar_caso_api(client, csrf_de(ADMIN), cliente.id)
        resp = client.post(
            "/api/compromissos",
            json={"caso_id": caso["id"], "titulo": "Sem CSRF",
                  "tipo": "REUNIAO", "data_inicio": "2026-12-10T09:00:00",
                  "data_fim": "2026-12-10T10:00:00"},
        )
        assert resp.status_code == 403


# --------------------------------------------------- compromissos: permissoes


def _payload_compromisso(caso_id=None, **extra):
    """Payload base de compromisso (amanha 9h-10h) para testes de status."""
    payload = {
        "titulo": "Compromisso de teste",
        "tipo": "REUNIAO",
        "data_inicio": "2026-12-10T09:00:00",
        "data_fim": "2026-12-10T10:00:00",
    }
    if caso_id is not None:
        payload["caso_id"] = caso_id
    payload.update(extra)
    return payload


class TestPermissoesCompromissos:
    """`pode_gerenciar_compromissos` e permissao PROPRIA (Fase 4)."""

    def test_grant_compromissos_concede_escrita_201(
        self, client, csrf_de, funcionario, criar_caso, conceder_acesso
    ):
        caso = criar_caso()
        conceder_acesso(caso, funcionario, pode_gerenciar_compromissos=True)
        resp = client.post(
            "/api/compromissos",
            headers={CSRF: csrf_de(FUNCIONARIO)},
            json=_payload_compromisso(caso_id=caso.id),
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["criado_por"] == funcionario.id

    def test_grant_prazos_nao_concede_compromissos_403(
        self, client, csrf_de, funcionario, criar_caso, conceder_acesso
    ):
        """`pode_gerenciar_prazos` NAO autoriza a agenda implicitamente."""
        caso = criar_caso()
        conceder_acesso(caso, funcionario, pode_gerenciar_prazos=True)
        resp = client.post(
            "/api/compromissos",
            headers={CSRF: csrf_de(FUNCIONARIO)},
            json=_payload_compromisso(caso_id=caso.id),
        )
        assert resp.status_code == 403, resp.text

    def test_grant_visualizar_somente_403(
        self, client, csrf_de, funcionario, criar_caso, conceder_acesso
    ):
        caso = criar_caso()
        conceder_acesso(caso, funcionario)  # so pode_visualizar
        resp = client.post(
            "/api/compromissos",
            headers={CSRF: csrf_de(FUNCIONARIO)},
            json=_payload_compromisso(caso_id=caso.id),
        )
        assert resp.status_code == 403, resp.text

    def test_sem_acesso_ao_caso_404(
        self, client, csrf_de, funcionario, criar_caso
    ):
        caso = criar_caso()
        resp = client.post(
            "/api/compromissos",
            headers={CSRF: csrf_de(FUNCIONARIO)},
            json=_payload_compromisso(caso_id=caso.id),
        )
        assert resp.status_code == 404, resp.text

    def test_concessao_via_api_propaga_201(
        self, client, csrf_de, advogada, criar_caso
    ):
        caso = criar_caso()
        # sem NENHUM grant: fora do escopo -> 404 (nao vaza o caso)
        resp = client.post(
            "/api/compromissos", headers={CSRF: csrf_de(PADRAO)},
            json=_payload_compromisso(caso_id=caso.id),
        )
        assert resp.status_code == 404, resp.text
        # admin concede apenas a visualizacao (menor privilegio)
        r = client.post(
            f"/api/casos/{caso.id}/usuarios",
            headers={CSRF: csrf_de(ADMIN)},
            json={"usuario_id": advogada.id},
        )
        assert r.status_code == 201, r.text
        assert r.json()["pode_gerenciar_compromissos"] is False
        # visivel, mas sem a permissao PROPRIA de escrita -> 403
        resp = client.post(
            "/api/compromissos", headers={CSRF: csrf_de(PADRAO)},
            json=_payload_compromisso(caso_id=caso.id),
        )
        assert resp.status_code == 403, resp.text
        # admin revoga e re-concede ja com a permissao de compromissos
        r = client.delete(
            f"/api/casos/{caso.id}/usuarios/{advogada.id}",
            headers={CSRF: csrf_de(ADMIN)},
        )
        assert r.status_code == 204, r.text
        r = client.post(
            f"/api/casos/{caso.id}/usuarios",
            headers={CSRF: csrf_de(ADMIN)},
            json={"usuario_id": advogada.id, "pode_gerenciar_compromissos": True},
        )
        assert r.status_code == 201, r.text  # reativacao da mesma linha
        assert r.json()["pode_gerenciar_compromissos"] is True
        # com o grant ativo a mesma advogada cadastra
        resp = client.post(
            "/api/compromissos", headers={CSRF: csrf_de(PADRAO)},
            json=_payload_compromisso(caso_id=caso.id),
        )
        assert resp.status_code == 201, resp.text

    def test_revogacao_remove_o_acesso_404(
        self, client, csrf_de, funcionario, criar_caso, conceder_acesso
    ):
        caso = criar_caso()
        conceder_acesso(caso, funcionario, pode_gerenciar_compromissos=True)
        csrf_de(FUNCIONARIO)
        # admin revoga o acesso (soft: ativo = False)
        r = client.delete(
            f"/api/casos/{caso.id}/usuarios/{funcionario.id}",
            headers={CSRF: csrf_de(ADMIN)},
        )
        assert r.status_code == 204, r.text
        # volta para a sessao do funcionario (cookie foi trocado pelo admin)
        resp = client.post(
            "/api/compromissos", headers={CSRF: csrf_de(FUNCIONARIO)},
            json=_payload_compromisso(caso_id=caso.id),
        )
        assert resp.status_code == 404, resp.text

    def test_responsavel_do_caso_cadastra_201(
        self, client, csrf_de, advogada, criar_cliente
    ):
        """O responsavel do caso mantem acesso a agenda (sem grant extra).

        A criacao do caso via API ja gera a linha de acesso do responsavel
        (mesma regra da Fase 1) e ele nao precisa do grant de compromissos.
        """
        cliente = criar_cliente(nome="Resp comp")
        caso = _criar_caso_api(
            client, csrf_de(ADMIN), cliente.id, responsavel_id=advogada.id
        )
        resp = client.post(
            "/api/compromissos",
            headers={CSRF: csrf_de(PADRAO)},
            json=_payload_compromisso(caso_id=caso["id"]),
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["responsavel_id"] == advogada.id


# ----------------------------------------------- compromissos: consulta/filtros


class TestConsultaCompromissos:
    def test_detalhe_200_e_escopo_404(
        self, client, csrf_de, advogada, criar_caso
    ):
        caso = criar_caso()
        comp = _criar_compromisso(client, csrf_de(ADMIN), caso_id=caso.id)

        # advogada sem grant: mesmo codigo do 404 (nao vaza caso alheio)
        csrf_de(PADRAO)
        assert client.get(f"/api/compromissos/{comp['id']}").status_code == 404

        # com grant de compromissos passa a enxergar
        r = client.post(
            f"/api/casos/{caso.id}/usuarios",
            headers={CSRF: csrf_de(ADMIN)},
            json={"usuario_id": advogada.id, "pode_gerenciar_compromissos": True},
        )
        assert r.status_code == 201, r.text
        csrf_de(PADRAO)
        resp = client.get(f"/api/compromissos/{comp['id']}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["id"] == comp["id"]

    def test_detalhe_inexistente_404(self, client, csrf_de):
        csrf_de(ADMIN)
        assert client.get("/api/compromissos/99999").status_code == 404

    def test_compromisso_sem_caso_invisivel_para_nao_admin(
        self, client, csrf_de, advogada, criar_caso
    ):
        """Sem caso: somente o administrador enxerga (agenda nunca publica)."""
        comp = _criar_compromisso(client, csrf_de(ADMIN))  # sem caso_id
        assert comp["caso_id"] is None

        csrf_de(PADRAO)
        assert client.get(f"/api/compromissos/{comp['id']}").status_code == 404
        lista = client.get("/api/compromissos?limite=100")
        assert lista.json()["total"] == 0

    def test_filtros(self, client, csrf_de, criar_caso, admin):
        caso_a = criar_caso(cliente="Filtro A")
        caso_b = criar_caso(cliente="Filtro B")
        csrf = csrf_de(ADMIN)
        proc = _criar_processo(client, csrf, caso_a.id, seq=10)
        amanha = (hoje_brasilia() + timedelta(days=1)).isoformat()
        distante = (hoje_brasilia() + timedelta(days=5)).isoformat()

        c1 = _criar_compromisso(
            client, csrf, caso_id=caso_a.id, processo_id=proc["id"],
            titulo="Audiencia marcada", tipo="AUDIENCIA",
            data_inicio=f"{amanha}T09:00:00", data_fim=f"{amanha}T11:00:00",
        )
        c2 = _criar_compromisso(
            client, csrf, caso_id=caso_b.id,
            titulo="Reuniao de alinhamento", tipo="REUNIAO",
            data_inicio=f"{distante}T14:00:00", data_fim=f"{distante}T15:00:00",
        )
        # cancela c2 para exercitar o filtro de status
        r = client.patch(
            f"/api/compromissos/{c2['id']}/status",
            headers={CSRF: csrf}, json={"status": "CANCELADO"},
        )
        assert r.status_code == 200, r.text

        def busca(params):
            resp = client.get(f"/api/compromissos?{params}&limite=100")
            assert resp.status_code == 200, resp.text
            return {i["id"] for i in resp.json()["itens"]}

        assert busca("q=Audiencia") == {c1["id"]}
        assert busca("q=alinhamento") == {c2["id"]}
        assert busca(f"caso_id={caso_a.id}") == {c1["id"]}
        assert busca(f"processo_id={proc['id']}") == {c1["id"]}
        assert busca("tipo=AUDIENCIA") == {c1["id"]}
        assert busca("tipo=REUNIAO") == {c2["id"]}
        assert busca("status=CANCELADO") == {c2["id"]}
        assert busca("status=AGENDADO") == {c1["id"]}
        assert busca(f"responsavel_id={admin.id}") == {c1["id"], c2["id"]}
        assert busca(f"inicio_de={amanha}&inicio_ate={amanha}") == {c1["id"]}
        assert busca(f"inicio_de={distante}") == {c2["id"]}

    def test_paginacao_no_banco(self, client, csrf_de, criar_caso):
        caso = criar_caso(cliente="Pagina comp")
        csrf = csrf_de(ADMIN)
        for n in range(3):
            _criar_compromisso(
                client, csrf, caso_id=caso.id, titulo=f"Compromisso {n}"
            )
        p1 = client.get("/api/compromissos?pagina=1&limite=2").json()
        p2 = client.get("/api/compromissos?pagina=2&limite=2").json()
        assert p1["total"] == 3 and len(p1["itens"]) == 2
        assert p2["total"] == 3 and len(p2["itens"]) == 1
        ids1 = {i["id"] for i in p1["itens"]}
        ids2 = {i["id"] for i in p2["itens"]}
        assert not ids1 & ids2  # paginas disjuntas

    def test_listagem_respeita_escopo(
        self, client, csrf_de, advogada, criar_caso
    ):
        meu = criar_caso(cliente="Meu comp")
        alheio = criar_caso(cliente="Alheio comp")
        sem_grant = criar_caso(cliente="Sem grant comp")
        csrf = csrf_de(ADMIN)
        _criar_compromisso(client, csrf, caso_id=meu.id, titulo="Do meu caso")
        _criar_compromisso(client, csrf, caso_id=alheio.id, titulo="Alheio")
        _criar_compromisso(client, csrf, caso_id=sem_grant.id, titulo="Sem grant")
        _criar_compromisso(client, csrf, titulo="Sem caso (admin)")

        # advogada com grant SOMENTE no caso "meu"
        r = client.post(
            f"/api/casos/{meu.id}/usuarios",
            headers={CSRF: csrf},
            json={"usuario_id": advogada.id, "pode_gerenciar_compromissos": True},
        )
        assert r.status_code == 201, r.text
        csrf_de(PADRAO)
        resp = client.get("/api/compromissos?limite=100")
        assert resp.status_code == 200, resp.text
        titulos = {i["titulo"] for i in resp.json()["itens"]}
        assert titulos == {"Do meu caso"}
        # contorno via filtro de caso alheio
        fuga = client.get(f"/api/compromissos?caso_id={sem_grant.id}")
        assert fuga.json()["total"] == 0

    def test_sem_sessao_401(self, client):
        assert client.get("/api/compromissos").status_code == 401
        assert client.get("/api/compromissos/1").status_code == 401


# ------------------------------------------------- compromissos: PATCH/status


class TestEdicaoCompromisso:
    def test_patch_parcial_200(self, client, csrf_de, criar_caso):
        caso = criar_caso(cliente="Edita comp")
        comp = _criar_compromisso(client, csrf_de(ADMIN), caso_id=caso.id)
        resp = client.patch(
            f"/api/compromissos/{comp['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"titulo": "Titulo revisado", "local": "Sala 2"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["titulo"] == "Titulo revisado"
        assert resp.json()["local"] == "Sala 2"

    def test_patch_com_periodo_invalido_422(self, client, csrf_de, criar_caso):
        caso = criar_caso(cliente="Periodo comp patch")
        comp = _criar_compromisso(client, csrf_de(ADMIN), caso_id=caso.id)
        amanha = (hoje_brasilia() + timedelta(days=1)).isoformat()
        # inicio padrao 9h: data_fim atual 10h - comecar as 11h inverte
        resp = client.patch(
            f"/api/compromissos/{comp['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"data_inicio": f"{amanha}T11:00:00"},
        )
        assert resp.status_code == 422, resp.text
        # o compromisso nao foi alterado
        detalhe = client.get(f"/api/compromissos/{comp['id']}").json()
        assert detalhe["data_inicio"] == f"{amanha}T09:00:00"

    def test_patch_nao_aceita_campos_proibidos(self, client, csrf_de, criar_caso):
        caso = criar_caso(cliente="Proibido comp")
        outro = criar_caso(cliente="Outro comp")
        comp = _criar_compromisso(client, csrf_de(ADMIN), caso_id=caso.id)
        csrf = csrf_de(ADMIN)
        for proibido in (
            {"caso_id": outro.id},
            {"processo_id": 1},
            {"status": "CANCELADO"},
            {"criado_por": 999},
            {"id": 1},
        ):
            resp = client.patch(
                f"/api/compromissos/{comp['id']}", headers={CSRF: csrf},
                json=proibido,
            )
            assert resp.status_code == 422, (proibido, resp.text)
        detalhe = client.get(f"/api/compromissos/{comp['id']}").json()
        assert detalhe["caso_id"] == caso.id
        assert detalhe["status"] == "AGENDADO"

    def test_patch_responsavel_sem_acesso_422(
        self, client, csrf_de, advogada, criar_caso
    ):
        caso = criar_caso(cliente="Resp comp")
        comp = _criar_compromisso(client, csrf_de(ADMIN), caso_id=caso.id)
        resp = client.patch(
            f"/api/compromissos/{comp['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"responsavel_id": advogada.id},  # sem grant no caso
        )
        assert resp.status_code == 422, resp.text

    def test_patch_sem_permissao_403(
        self, client, csrf_de, funcionario, criar_caso, conceder_acesso
    ):
        caso = criar_caso(cliente="Sem grant edit")
        comp = _criar_compromisso(client, csrf_de(ADMIN), caso_id=caso.id)
        conceder_acesso(caso, funcionario)  # so pode_visualizar
        resp = client.patch(
            f"/api/compromissos/{comp['id']}",
            headers={CSRF: csrf_de(FUNCIONARIO)},
            json={"titulo": "Nao pode"},
        )
        assert resp.status_code == 403, resp.text

    def test_patch_fora_do_escopo_404(self, client, csrf_de, criar_caso):
        caso = criar_caso(cliente="Escopo comp")
        comp = _criar_compromisso(client, csrf_de(ADMIN), caso_id=caso.id)
        resp = client.patch(
            f"/api/compromissos/{comp['id']}",
            headers={CSRF: csrf_de(PADRAO)},
            json={"titulo": "Invadindo"},
        )
        assert resp.status_code == 404, resp.text


class TestStatusCompromisso:
    """O status muda SOMENTE pela rota `/status` (nao pelo payload)."""

    def test_agendado_para_realizado_200(self, client, csrf_de, criar_caso, admin):
        caso = criar_caso(cliente="Status comp")
        comp = _criar_compromisso(client, csrf_de(ADMIN), caso_id=caso.id)
        resp = client.patch(
            f"/api/compromissos/{comp['id']}/status",
            headers={CSRF: csrf_de(ADMIN)}, json={"status": "REALIZADO"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "REALIZADO"
        hist = client.get(f"/api/compromissos/{comp['id']}/historico").json()
        mudanca = [h for h in hist if h["operacao"] == "ATUALIZACAO"]
        assert len(mudanca) == 1
        assert mudanca[0]["dados"]["status"] == {
            "antes": "AGENDADO", "depois": "REALIZADO",
        }
        assert mudanca[0]["usuario_id"] == admin.id

    def test_cancelar_registra_operacao_cancelamento(
        self, client, csrf_de, criar_caso
    ):
        caso = criar_caso(cliente="Cancela comp")
        comp = _criar_compromisso(client, csrf_de(ADMIN), caso_id=caso.id)
        resp = client.patch(
            f"/api/compromissos/{comp['id']}/status",
            headers={CSRF: csrf_de(ADMIN)}, json={"status": "CANCELADO"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "CANCELADO"
        hist = client.get(f"/api/compromissos/{comp['id']}/historico").json()
        assert [h["operacao"] for h in hist] == ["CANCELAMENTO", "CRIACAO"]
        cancelamento = hist[0]
        assert cancelamento["dados"]["status"]["antes"] == "AGENDADO"
        assert cancelamento["dados"]["status"]["depois"] == "CANCELADO"

    def test_status_igual_nao_grava_historico(
        self, client, csrf_de, criar_caso
    ):
        caso = criar_caso(cliente="Igual comp")
        comp = _criar_compromisso(client, csrf_de(ADMIN), caso_id=caso.id)
        resp = client.patch(
            f"/api/compromissos/{comp['id']}/status",
            headers={CSRF: csrf_de(ADMIN)}, json={"status": "AGENDADO"},
        )
        assert resp.status_code == 200, resp.text
        hist = client.get(f"/api/compromissos/{comp['id']}/historico").json()
        assert [h["operacao"] for h in hist] == ["CRIACAO"]

    def test_status_invalido_422(self, client, csrf_de, criar_caso):
        caso = criar_caso(cliente="Status ruim")
        comp = _criar_compromisso(client, csrf_de(ADMIN), caso_id=caso.id)
        csrf = csrf_de(ADMIN)
        for payload in (
            {"status": "FINALIZADO"},
            {"status": "PENDENTE"},  # status de prazo, nao de compromisso
            {},
            {"status": "AGENDADO", "extra": 1},
        ):
            resp = client.patch(
                f"/api/compromissos/{comp['id']}/status",
                headers={CSRF: csrf}, json=payload,
            )
            assert resp.status_code == 422, (payload, resp.text)

    def test_status_sem_permissao_403(
        self, client, csrf_de, funcionario, criar_caso, conceder_acesso
    ):
        caso = criar_caso(cliente="Status sem grant")
        comp = _criar_compromisso(client, csrf_de(ADMIN), caso_id=caso.id)
        conceder_acesso(caso, funcionario, pode_gerenciar_prazos=True)
        resp = client.patch(
            f"/api/compromissos/{comp['id']}/status",
            headers={CSRF: csrf_de(FUNCIONARIO)}, json={"status": "REALIZADO"},
        )
        assert resp.status_code == 403, resp.text

    def test_status_fora_do_escopo_404(self, client, csrf_de, criar_caso):
        caso = criar_caso(cliente="Status escopo")
        comp = _criar_compromisso(client, csrf_de(ADMIN), caso_id=caso.id)
        resp = client.patch(
            f"/api/compromissos/{comp['id']}/status",
            headers={CSRF: csrf_de(PADRAO)}, json={"status": "CANCELADO"},
        )
        assert resp.status_code == 404, resp.text


# --------------------------------------------------------------- /api/agenda


class TestAgenda:
    def test_periodo_padrao_hoje_ate_30_dias(self, client, csrf_de, criar_caso):
        caso = criar_caso(cliente="Agenda padrao")
        _criar_compromisso(client, csrf_de(ADMIN), caso_id=caso.id)  # amanha
        resp = client.get("/api/agenda")
        assert resp.status_code == 200, resp.text
        corpo = resp.json()
        hoje = hoje_brasilia()
        assert corpo["de"] == hoje.isoformat()
        assert corpo["ate"] == (hoje + timedelta(days=30)).isoformat()
        assert corpo["total"] == 1
        assert len(corpo["itens"]) == 1
        assert corpo["itens"][0]["data_inicio"] < corpo["itens"][0]["data_fim"]

    def test_sobreposicao_evento_que_atravessa_dias(
        self, client, csrf_de, criar_caso
    ):
        """Evento que comeca antes de `de` e termina dentro dele entra."""
        caso = criar_caso(cliente="Sobreposicao")
        csrf = csrf_de(ADMIN)
        hoje = hoje_brasilia()
        d5, d6, d4 = (
            (hoje + timedelta(days=n)).isoformat() for n in (5, 6, 4)
        )
        cruzando = _criar_compromisso(
            client, csrf, caso_id=caso.id, titulo="Vigilia noturna",
            data_inicio=f"{d5}T22:00:00", data_fim=f"{d6}T06:00:00",
        )
        dentro = _criar_compromisso(
            client, csrf, caso_id=caso.id, titulo="Dentro do dia",
            data_inicio=f"{d6}T10:00:00", data_fim=f"{d6}T11:00:00",
        )
        antes = _criar_compromisso(
            client, csrf, caso_id=caso.id, titulo="Antes do periodo",
            data_inicio=f"{d4}T08:00:00", data_fim=f"{d4}T09:00:00",
        )

        resp = client.get(f"/api/agenda?de={d6}&ate={d6}")
        assert resp.status_code == 200, resp.text
        ids = {i["id"] for i in resp.json()["itens"]}
        assert ids == {cruzando["id"], dentro["id"]}
        assert antes["id"] not in ids

        # recorte que comeca no dia do evento noturno: ele tambem entra
        resp = client.get(f"/api/agenda?de={d5}&ate={d6}")
        ids = {i["id"] for i in resp.json()["itens"]}
        assert ids == {cruzando["id"], dentro["id"]}
        # ordenado por horario de inicio
        itens = resp.json()["itens"]
        assert itens[0]["id"] == cruzando["id"]

    def test_ate_menor_que_de_422(self, client, csrf_de):
        csrf_de(ADMIN)
        resp = client.get("/api/agenda?de=2026-12-10&ate=2026-12-01")
        assert resp.status_code == 422, resp.text

    def test_periodo_limitado_a_366_dias(self, client, csrf_de):
        csrf_de(ADMIN)
        ruim = client.get("/api/agenda?de=2026-01-01&ate=2027-01-03")
        assert ruim.status_code == 422, ruim.text  # 367 dias
        no_limite = client.get("/api/agenda?de=2026-01-01&ate=2027-01-02")
        assert no_limite.status_code == 200, no_limite.text  # 366 dias

    def test_agenda_nao_mistura_prazos(self, client, csrf_de, criar_caso):
        caso = criar_caso(cliente="Agenda sem prazos")
        csrf = csrf_de(ADMIN)
        _criar_prazo(
            client, csrf, caso.id,
            titulo="Prazo que nao aparece",
            data_vencimento=(hoje_brasilia() + timedelta(days=2)).isoformat(),
        )
        _criar_compromisso(client, csrf, caso_id=caso.id)
        resp = client.get("/api/agenda")
        assert resp.status_code == 200, resp.text
        corpo = resp.json()
        assert corpo["total"] == 1  # so o compromisso; prazo nunca entra
        item = corpo["itens"][0]
        assert "data_vencimento" not in item
        assert "situacao" not in item
        assert "data_inicio" in item and "data_fim" in item

    def test_agenda_filtro_responsavel(self, client, csrf_de, criar_caso, admin):
        caso = criar_caso(cliente="Agenda responsavel")
        csrf = csrf_de(ADMIN)
        _criar_compromisso(client, csrf, caso_id=caso.id, titulo="Do admin")
        resp = client.get(f"/api/agenda?responsavel_id={admin.id}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["total"] == 1
        outro = client.get(f"/api/agenda?responsavel_id={admin.id + 999}")
        assert outro.json()["total"] == 0

    def test_agenda_respeita_escopo(
        self, client, csrf_de, advogada, criar_caso
    ):
        meu = criar_caso(cliente="Agenda meu")
        alheio = criar_caso(cliente="Agenda alheio")
        csrf = csrf_de(ADMIN)
        _criar_compromisso(client, csrf, caso_id=meu.id, titulo="Meu evento")
        _criar_compromisso(client, csrf, caso_id=alheio.id, titulo="Alheio")
        _criar_compromisso(client, csrf, titulo="Pessoal do admin")
        r = client.post(
            f"/api/casos/{meu.id}/usuarios",
            headers={CSRF: csrf},
            json={"usuario_id": advogada.id},
        )
        assert r.status_code == 201, r.text

        csrf_de(PADRAO)
        corpo = client.get("/api/agenda?limite=100").json()
        titulos = {i["titulo"] for i in corpo["itens"]}
        assert titulos == {"Meu evento"}
        # nem o evento pessoal do admin nem os de casos alheios vazam
        assert corpo["total"] == 1

    def test_agenda_sem_sessao_401(self, client):
        assert client.get("/api/agenda").status_code == 401


# ------------------------------------- compromissos: auditoria e atomicidade


class TestHistoricoCompromisso:
    def test_criacao_gera_registro(self, client, csrf_de, criar_caso, admin):
        caso = criar_caso(cliente="Hist comp")
        comp = _criar_compromisso(client, csrf_de(ADMIN), caso_id=caso.id)
        hist = client.get(f"/api/compromissos/{comp['id']}/historico")
        assert hist.status_code == 200, hist.text
        assert [h["operacao"] for h in hist.json()] == ["CRIACAO"]
        assert hist.json()[0]["usuario_id"] == admin.id

    def test_atualizacao_registra_antes_depois(self, client, csrf_de, criar_caso):
        caso = criar_caso(cliente="Hist update comp")
        comp = _criar_compromisso(client, csrf_de(ADMIN), caso_id=caso.id)
        client.patch(
            f"/api/compromissos/{comp['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"titulo": "Titulo alterado", "local": "Foro Central"},
        )
        hist = client.get(f"/api/compromissos/{comp['id']}/historico").json()
        atualizacao = [h for h in hist if h["operacao"] == "ATUALIZACAO"]
        assert len(atualizacao) == 1
        dados = atualizacao[0]["dados"]
        assert dados["titulo"]["antes"] == "Compromisso da Fase 4"
        assert dados["titulo"]["depois"] == "Titulo alterado"
        assert dados["local"]["depois"] == "Foro Central"

    def test_mudanca_responsavel_entrada_propria(
        self, client, csrf_de, advogada, criar_caso, admin
    ):
        caso = criar_caso(cliente="Hist resp comp")
        comp = _criar_compromisso(client, csrf_de(ADMIN), caso_id=caso.id)
        # advogada com acesso ao caso para poder assumir o compromisso
        r = client.post(
            f"/api/casos/{caso.id}/usuarios",
            headers={CSRF: csrf_de(ADMIN)},
            json={"usuario_id": advogada.id},
        )
        assert r.status_code == 201, r.text
        resp = client.patch(
            f"/api/compromissos/{comp['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"responsavel_id": advogada.id},
        )
        assert resp.status_code == 200, resp.text
        hist = client.get(f"/api/compromissos/{comp['id']}/historico").json()
        mudanca = [h for h in hist if h["operacao"] == "MUDANCA_RESPONSAVEL"]
        assert len(mudanca) == 1
        # era o operador (admin) e passou para a advogada
        assert mudanca[0]["dados"]["responsavel_id"]["antes"] == admin.id
        assert mudanca[0]["dados"]["responsavel_id"]["depois"] == advogada.id

    def test_atualizacao_identica_nao_grava(self, client, csrf_de, criar_caso):
        caso = criar_caso(cliente="Hist igual comp")
        comp = _criar_compromisso(client, csrf_de(ADMIN), caso_id=caso.id)
        resp = client.patch(
            f"/api/compromissos/{comp['id']}",
            headers={CSRF: csrf_de(ADMIN)},
            json={"titulo": "Compromisso da Fase 4"},  # mesmo valor
        )
        assert resp.status_code == 200, resp.text
        hist = client.get(f"/api/compromissos/{comp['id']}/historico").json()
        assert [h["operacao"] for h in hist] == ["CRIACAO"]

    def test_historico_escopo_e_sem_escrita(self, client, csrf_de, criar_caso):
        caso = criar_caso(cliente="Hist escopo comp")
        comp = _criar_compromisso(client, csrf_de(ADMIN), caso_id=caso.id)

        csrf_de(PADRAO)
        resp = client.get(f"/api/compromissos/{comp['id']}/historico")
        assert resp.status_code == 404, resp.text

        # o historico e imutavel: nenhuma rota de escrita
        escrita = client.post(
            f"/api/compromissos/{comp['id']}/historico",
            headers={CSRF: csrf_de(ADMIN)},
            json={"operacao": "FALSO", "dados": {}},
        )
        assert escrita.status_code in (404, 405)


class TestAtomicidadeCompromisso:
    """Negocio + auditoria compartilham UMA transacao (rollback total)."""

    def test_falha_na_auditoria_desfaz_a_criacao(
        self, client, csrf_de, criar_caso, db_session, monkeypatch
    ):
        from app.models.compromisso import Compromisso
        from app.repositories.compromisso_historico_repository import (
            CompromissoHistoricoRepository,
        )

        caso = criar_caso(cliente="Atomico comp")
        monkeypatch.setattr(
            CompromissoHistoricoRepository, "registrar", _falha_de_auditoria
        )
        with pytest.raises(RuntimeError, match="auditoria"):
            client.post(
                "/api/compromissos",
                headers={CSRF: csrf_de(ADMIN)},
                json=_payload_compromisso(caso_id=caso.id),
            )
        db_session.expire_all()
        persistido = (
            db_session.query(Compromisso)
            .filter(Compromisso.titulo == "Compromisso de teste")
            .count()
        )
        assert persistido == 0, "compromisso criado sem a sua auditoria"

    def test_falha_na_auditoria_desfaz_o_status(
        self, client, csrf_de, criar_caso, db_session, monkeypatch
    ):
        from app.models.compromisso import Compromisso
        from app.repositories.compromisso_historico_repository import (
            CompromissoHistoricoRepository,
        )

        caso = criar_caso(cliente="Atomico status")
        comp = _criar_compromisso(client, csrf_de(ADMIN), caso_id=caso.id)

        monkeypatch.setattr(
            CompromissoHistoricoRepository, "registrar", _falha_de_auditoria
        )
        with pytest.raises(RuntimeError, match="auditoria"):
            client.patch(
                f"/api/compromissos/{comp['id']}/status",
                headers={CSRF: csrf_de(ADMIN)},
                json={"status": "REALIZADO"},
            )
        db_session.expire_all()
        objeto = db_session.get(Compromisso, comp["id"])
        assert objeto.status == "AGENDADO", "status mudou sem auditoria"

    def test_falha_na_auditoria_desfaz_a_edicao(
        self, client, csrf_de, criar_caso, db_session, monkeypatch
    ):
        from app.models.compromisso import Compromisso
        from app.repositories.compromisso_historico_repository import (
            CompromissoHistoricoRepository,
        )

        caso = criar_caso(cliente="Atomico edit comp")
        comp = _criar_compromisso(client, csrf_de(ADMIN), caso_id=caso.id)

        monkeypatch.setattr(
            CompromissoHistoricoRepository, "registrar", _falha_de_auditoria
        )
        with pytest.raises(RuntimeError, match="auditoria"):
            client.patch(
                f"/api/compromissos/{comp['id']}",
                headers={CSRF: csrf_de(ADMIN)},
                json={"titulo": "Alteracao invalida"},
            )
        db_session.expire_all()
        objeto = db_session.get(Compromisso, comp["id"])
        assert objeto.titulo == "Compromisso da Fase 4"


# ------------------------------------------------------- tempo local (UTC-3)


class TestTempoBrasilia:
    def test_fuso_fixo_utc_menos_3(self):
        from app.core.tempo import BRASILIA

        assert BRASILIA.utcoffset(None) == timedelta(hours=-3)

    def test_agora_brasilia_naive_e_deslocada_de_utc(self):
        from app.core.tempo import agora_brasilia
        from app.models.usuario import utcnow

        agora = agora_brasilia()
        assert agora.tzinfo is None  # naive, compativel com DATETIME do banco
        # Brasilia = UTC-3 (sem horario de verao desde 2019)
        diferenca = agora - utcnow()
        assert abs(diferenca + timedelta(hours=3)) < timedelta(seconds=10)

    def test_hoje_e_a_data_local_de_brasilia(self):
        from app.core.tempo import agora_brasilia, hoje_brasilia
        from app.models.usuario import utcnow

        brasil = agora_brasilia()
        assert hoje_brasilia() == brasil.date()
        # UTC-3: o dia UTC pode estar a frente no maximo em 1 dia (nunca atras)
        dia_utc = utcnow().date()
        if dia_utc != brasil.date():
            assert dia_utc - brasil.date() == timedelta(days=1)

    def test_datetime_com_fuso_converte_para_brasilia(
        self, client, csrf_de, criar_caso
    ):
        """Horario com fuso e gravado no horario LOCAL do escritorio."""
        caso = criar_caso(cliente="Fuso")
        resp = client.post(
            "/api/compromissos",
            headers={CSRF: csrf_de(ADMIN)},
            json=_payload_compromisso(
                caso_id=caso.id,
                data_inicio="2026-12-10T12:00:00+00:00",  # UTC
                data_fim="2026-12-10T14:00:00+00:00",
            ),
        )
        assert resp.status_code == 201, resp.text
        corpo = resp.json()
        # 12:00 UTC = 09:00 em Brasilia (UTC-3 fixo)
        assert corpo["data_inicio"] == "2026-12-10T09:00:00"
        assert corpo["data_fim"] == "2026-12-10T11:00:00"
