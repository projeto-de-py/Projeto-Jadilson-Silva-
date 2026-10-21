"""Processos acompanhados pelo escritorio."""
from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.usuario import utcnow


class Caso(Base):
    __tablename__ = "casos"
    __table_args__ = (UniqueConstraint("numero_processo", name="uq_casos_numero_processo"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero_processo: Mapped[str] = mapped_column(String(30), nullable=False)
    cliente: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    parte_contraria: Mapped[str | None] = mapped_column(String(160))
    tribunal: Mapped[str | None] = mapped_column(String(120))
    vara: Mapped[str | None] = mapped_column(String(160))
    area: Mapped[str] = mapped_column(String(80), nullable=False, default="Civel")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="EM_ANDAMENTO", index=True)
    descricao: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    prazos: Mapped[list["Prazo"]] = relationship(back_populates="caso", cascade="all, delete-orphan")
    andamentos: Mapped[list["Andamento"]] = relationship(back_populates="caso", cascade="all, delete-orphan")
