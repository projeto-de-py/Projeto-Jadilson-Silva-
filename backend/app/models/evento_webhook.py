"""Eventos de webhook ja processados (idempotencia: o mesmo evento nao age duas vezes)."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.usuario import utcnow


class EventoWebhook(Base):
    __tablename__ = "eventos_webhook"
    __table_args__ = (UniqueConstraint("origem", "evento_id", name="uq_evento_webhook"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    origem: Mapped[str] = mapped_column(String(20), nullable=False)  # zapsign | asaas
    evento_id: Mapped[str] = mapped_column(String(160), nullable=False)
    tipo: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
