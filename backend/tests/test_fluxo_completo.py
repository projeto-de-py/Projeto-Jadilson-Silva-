"""E2E do fluxo principal: login → cliente → caso → processo → prazo/agenda
→ andamento → documento, com CSRF e notificação gravada no evento de escrita.

Roda em SQLite em memória (mesma suíte); a versão contra MySQL está em
`backend/scripts/smoke_mysql.py`.
"""

from datetime import date, datetime, timedelta

from conftest import gerar_numero_cnj

from app.repositories.notificacao_repository import NotificacaoRepository


def test_fluxo_completo_ponta_a_ponta(client, csrf_admin, db_session):
    cabecalho = {"X-CSRF-Token": csrf_admin}
    assert client.get("/api/auth/me").status_code == 200

    cliente = client.post(
        "/api/clientes", json={"nome": "Cliente E2E Completo"}, headers=cabecalho
    )
    assert cliente.status_code == 201, cliente.text
    cliente_id = cliente.json()["id"]

    caso = client.post(
        "/api/casos",
        json={
            "titulo": "Caso E2E Completo",
            "cliente_id": cliente_id,
            "area": "PREVIDENCIARIO",
        },
        headers=cabecalho,
    )
    assert caso.status_code == 201, caso.text
    caso_id = caso.json()["id"]

    numero = gerar_numero_cnj(1)
    processo = client.post(
        f"/api/casos/{caso_id}/processos",
        json={"numero_processo": numero},
        headers=cabecalho,
    )
    assert processo.status_code == 201, processo.text
    processo_id = processo.json()["id"]
    consulta = client.get("/api/processos", params={"q": numero.replace("-", "")[:7]})
    assert consulta.status_code == 200
    assert consulta.json()["total"] == 1

    vencimento = date.today() + timedelta(days=1)
    prazo = client.post(
        "/api/prazos",
        json={
            "caso_id": caso_id,
            "titulo": "Prazo E2E Completo",
            "data_vencimento": vencimento.isoformat(),
            "prioridade": "ALTA",
        },
        headers=cabecalho,
    )
    assert prazo.status_code == 201, prazo.text
    prazo_id = prazo.json()["id"]

    inicio = datetime.now() + timedelta(days=2)
    compromisso = client.post(
        "/api/compromissos",
        json={
            "caso_id": caso_id,
            "titulo": "Audiencia E2E",
            "tipo": "AUDIENCIA",
            "data_inicio": inicio.isoformat(),
            "data_fim": (inicio + timedelta(hours=1)).isoformat(),
        },
        headers=cabecalho,
    )
    assert compromisso.status_code == 201, compromisso.text
    agenda = client.get(
        "/api/agenda",
        params={"de": inicio.date().isoformat(), "ate": inicio.date().isoformat()},
    )
    assert agenda.status_code == 200, agenda.text

    andamento = client.post(
        f"/api/casos/{caso_id}/andamentos",
        json={"titulo": "Andamento E2E", "descricao": "movimentado"},
        headers=cabecalho,
    )
    assert andamento.status_code == 201, andamento.text

    documento = client.post(
        "/api/documentos",
        json={
            "titulo": "Documento E2E",
            "caso_id": caso_id,
            "html": "<p>conteudo</p>",
        },
        headers=cabecalho,
    )
    assert documento.status_code == 201, documento.text
    documentos = client.get("/api/documentos", params={"limite": 200})
    assert documentos.status_code == 200
    assert any(d["id"] == documento.json()["id"] for d in documentos.json()["itens"])

    # RF09: os filtros chegam ao banco (não ao recorte de 100 itens da tela).
    for rota, termo in (
        ("clientes", "E2E Completo"),
        ("casos", "E2E Completo"),
        ("prazos", "E2E Completo"),
    ):
        filtrado = client.get(f"/api/{rota}", params={"q": termo})
        assert filtrado.status_code == 200, (rota, filtrado.text)
        assert filtrado.json()["total"] == 1, rota

    # Nenhuma leitura de /api/notificacoes aconteceu acima: o aviso já existe.
    aviso = NotificacaoRepository(db_session).buscar_dedupe(
        1, f"prazo:{prazo_id}:{vencimento.isoformat()}:marco-1"
    )
    assert aviso is not None
    assert f"E2E Completo" in aviso.titulo or "prazo" in aviso.mensagem.lower()

    assert processo_id > 0 and compromisso.json()["id"] > 0
