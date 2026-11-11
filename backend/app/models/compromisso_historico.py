"""Auditoria das alteracoes relevantes de um Compromisso (Fase 4).

Mesmo padrao de `prazo_historicos`/`processo_historicos`: registro imutavel,
sem endpoint de escrita, com os campos alterados (antes/depois) em `dados`.

Operacoes registradas: criacao, atualizacao, cancelamento e mudanca de
responsavel (secao 12 da Fase 4).
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.usuario import utcnow

# Tipos de operacao registradas no historico do compromisso.
OP_CRIACAO = "CRIACAO"
OP_ATUALIZACAO = "ATUALIZACAO"
OP_CANCELAMENTO = "CANCELAMENTO"
OP_MUDANCA_RESPONSAVEL = "MUDANCA_RESPONSAVEL"


class CompromissoHistorico(Base):
    __tablename__ = "compromisso_historicos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    compromisso_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("compromissos.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    usuario_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    operacao: Mapped[str] = mapped_column(String(30), nullable=False)
    dados: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    usuario: Mapped["Usuario | None"] = relationship("Usuario", lazy="selectin")

    def __repr__(self) -> str:
        return f"<CompromissoHistorico compromisso={self.compromisso_id} {self.operacao}>"
