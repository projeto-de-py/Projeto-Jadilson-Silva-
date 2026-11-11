"""Avisos internos destinados a uma conta, sem dados pessoais no texto."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.usuario import utcnow


class Notificacao(Base):
    __tablename__ = "notificacoes"
    __table_args__ = (UniqueConstraint("usuario_id", "chave_dedupe", name="uq_notificacao_usuario_dedupe"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    titulo: Mapped[str] = mapped_column(String(120), nullable=False)
    mensagem: Mapped[str] = mapped_column(String(240), nullable=False)
    link: Mapped[str] = mapped_column(String(300), nullable=False, default="/home")
    severidade: Mapped[str] = mapped_column(String(12), nullable=False, default="info")
    chave_dedupe: Mapped[str] = mapped_column(String(180), nullable=False)
    lida_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, index=True)
