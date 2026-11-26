"""Avisos automáticos gravados pelo servidor, sem depender da tela.

Cobre os dois caminhos introduzidos na Fase 4:
1. a varredura em segundo plano (`sincronizar_notificacoes_para_todos`);
2. o evento de escrita de prazo (POST/PATCH disparam a geração na hora).
"""

from datetime import date, timedelta

import pytest

from app.models.prazo import Prazo
from app.repositories.notificacao_repository import NotificacaoRepository
from app.services.notificacao_service import sincronizar_notificacoes_para_todos


@pytest.fixture
def quarta_controlada(monkeypatch):
    """Congela 'hoje' para não depender do dia da execução da suíte."""

    class DataControlada(date):
        @classmethod
        def today(cls):
            return cls(2026, 11, 4)  # quarta-feira

    monkeypatch.setattr("app.services.notificacao_service.date", DataControlada)
    return DataControlada.today()


def test_varredura_grava_aviso_sem_ler_tela(db_session, admin, criar_caso, quarta_controlada):
    caso = criar_caso(cliente="Cliente varredura", criado_por=admin.id)
    vencimento = quarta_controlada + timedelta(days=3)
    prazo = Prazo(
        caso_id=caso.id,
        titulo="Prazo da varredura",
        data_vencimento=vencimento,
        criado_por=admin.id,
    )
    db_session.add(prazo)
    db_session.commit()

    # Nenhuma rota de leitura é chamada: a rotina é disparada pelo servidor.
    processados = sincronizar_notificacoes_para_todos(db_session)
    assert processados >= 1

    repo = NotificacaoRepository(db_session)
    aviso = repo.buscar_dedupe(
        admin.id,
        f"prazo:{prazo.id}:{vencimento.isoformat()}:marco-3",
    )
    assert aviso is not None
    assert aviso.lida_em is None

    # Idempotente: repetir a varredura não duplica o aviso.
    sincronizar_notificacoes_para_todos(db_session)
    assert repo.contar_nao_lidas(admin.id) == 1


def test_criar_prazo_grava_aviso_no_evento(
    client, db_session, admin, csrf_admin, criar_caso, quarta_controlada
):
    caso = criar_caso(cliente="Cliente evento", criado_por=admin.id)
    vencimento = quarta_controlada + timedelta(days=1)
    resposta = client.post(
        "/api/prazos",
        json={
            "caso_id": caso.id,
            "titulo": "Prazo criado agora",
            "data_vencimento": vencimento.isoformat(),
            "prioridade": "ALTA",
        },
        headers={"X-CSRF-Token": csrf_admin},
    )
    assert resposta.status_code == 201, resposta.text
    prazo_id = resposta.json()["id"]

    # A consulta abaixo é direta ao repositório: prova que o aviso já existe
    # antes de qualquer GET /api/notificacoes.
    aviso = NotificacaoRepository(db_session).buscar_dedupe(
        admin.id,
        f"prazo:{prazo_id}:{vencimento.isoformat()}:marco-1",
    )
    assert aviso is not None
    assert aviso.titulo == "Prazo amanhã"
