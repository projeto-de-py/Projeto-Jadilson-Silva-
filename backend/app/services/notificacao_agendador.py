"""Varredura periódica de notificações automáticas.

Complementa os eventos de negócio (por exemplo, a criação de um prazo): mesmo
que ninguém abra o painel, o servidor roda os geradores em intervalos curtos e
grava os avisos no banco. A configuração `NOTIFICACOES_VARREDURA_MINUTOS`
permite desligar a tarefa (valor 0) — é o que fazem os testes, que usam SQLite
em memória e não devem tocar no banco real.
"""

import asyncio
import logging
from contextlib import suppress
from app.config import get_settings
from app.database import SessionLocal
from app.services.notificacao_service import sincronizar_notificacoes_para_todos

_LOG = logging.getLogger(__name__)


def _varrer_agora() -> None:
    db = SessionLocal()
    try:
        sincronizar_notificacoes_para_todos(db)
    finally:
        db.close()


async def _loop(minutos: int) -> None:
    while True:
        await asyncio.sleep(minutos * 60)
        try:
            # SQLAlchemy e sincrono: roda em thread para nao bloquear o loop
            # de eventos do uvicorn.
            await asyncio.to_thread(_varrer_agora)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - a tarefa deve sobreviver a falhas
            _LOG.exception("Falha na varredura automatica de notificacoes")


def iniciar_varredura() -> asyncio.Task | None:
    """Cria a tarefa assíncrona; devolve None quando desligada por config."""
    minutos = get_settings().notificacoes_varredura_minutos
    if minutos <= 0:
        return None
    # Usa `asyncio.create_task` diretamente: o lifespan já roda dentro do loop.
    return asyncio.create_task(_loop(minutos), name="varredura-notificacoes")


async def parar_varredura(tarefa: asyncio.Task | None) -> None:
    if tarefa is None:
        return
    tarefa.cancel()
    with suppress(asyncio.CancelledError):
        await tarefa
