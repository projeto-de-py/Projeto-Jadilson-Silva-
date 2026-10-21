"""Prazos vinculados a processos."""
from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.usuario import utcnow


class Prazo(Base):
    __tablename__ = "prazos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    caso_id: Mapped[int] = mapped_column(ForeignKey("casos.id", ondelete="CASCADE"), nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(160), nullable=False)
    tipo: Mapped[str] = mapped_column(String(60), nullable=False, default="PROCESSUAL")
    data_limite: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    descricao: Mapped[str | None] = mapped_column(Text)
    cumprido: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    caso: Mapped["Caso"] = relationship(back_populates="prazos")
