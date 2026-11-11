"""Auditoria do uso da IA (quem pediu o que, com qual versao de prompt).

Nunca guarda o texto do pedido nem do documento: so metadados (LGPD).
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.usuario import utcnow


class UsoIA(Base):
    __tablename__ = "uso_ia"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tarefa: Mapped[str] = mapped_column(String(20), nullable=False)
    area: Mapped[str | None] = mapped_column(String(20), nullable=True)
    provedor: Mapped[str] = mapped_column(String(30), nullable=False)
    versao_prompt: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    simulado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    bloqueado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    n_sugestoes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_entrada: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_saida: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duracao_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, index=True)
