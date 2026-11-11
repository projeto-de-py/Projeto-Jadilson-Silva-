"""Padrao Repository: eventos de webhook ja processados (idempotencia)."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.evento_webhook import EventoWebhook


class EventoWebhookRepository:
    def __init__(self, db: Session):
        self.db = db

    def registrar(self, origem: str, evento_id: str, tipo: str) -> bool:
        """Reserva o evento. False se ele ja foi processado (nao faz commit; o service confirma)."""
        self.db.add(EventoWebhook(origem=origem, evento_id=evento_id[:160], tipo=tipo[:60]))
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            return False
        return True
