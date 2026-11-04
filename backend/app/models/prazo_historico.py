"""Auditoria das alteracoes relevantes de um Prazo (Fase 4).

Espelha o padrao de `processo_historicos` (Fase 3): tabela propria, registro
imutavel do ponto de vista da API (nao existe endpoint de escrita) e `dados`
guardando somente os campos alterados (antes/depois).

Operacoes registradas: criacao, alteracao, conclusao, reabertura,
cancelamento, mudanca de responsavel e mudanca de vencimento.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.usuario import utcnow

# Tipos de operacao registradas no historico do prazo.
OP_CRIACAO = "CRIACAO"
OP_ATUALIZACAO = "ATUALIZACAO"
OP_CONCLUSAO = "CONCLUSAO"
OP_REABERTURA = "REABERTURA"
OP_CANCELAMENTO = "CANCELAMENTO"
OP_MUDANCA_RESPONSAVEL = "MUDANCA_RESPONSAVEL"
OP_MUDANCA_VENCIMENTO = "MUDANCA_VENCIMENTO"


class PrazoHistorico(Base):
    __tablename__ = "prazo_historicos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prazo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prazos.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    usuario_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    operacao: Mapped[str] = mapped_column(String(30), nullable=False)
    # Ex.: {"data_vencimento": {"antes": "2026-11-10", "depois": "2026-11-20"}}
    dados: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    usuario: Mapped["Usuario | None"] = relationship("Usuario", lazy="selectin")

    def __repr__(self) -> str:
        return f"<PrazoHistorico prazo={self.prazo_id} {self.operacao}>"
