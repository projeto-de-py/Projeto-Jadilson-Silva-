"""Evento compartilhado da agenda do escritorio."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.usuario import utcnow


class EventoAgenda(Base):
    __tablename__ = "eventos_agenda"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    titulo: Mapped[str] = mapped_column(String(120), nullable=False)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    inicio: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    duracao: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    local: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    descricao: Mapped[str] = mapped_column(Text, nullable=False, default="")
    destinatario_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=True, index=True
    )
    criado_por_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
