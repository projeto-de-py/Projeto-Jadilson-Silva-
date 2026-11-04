"""Auditoria das alteracoes relevantes de um Caso (Fase 2).

Registro imutavel do ponto de vista da API: nao existe endpoint de escrita -
o service grava as mudancas automaticamente. `dados` guarda somente os campos
alterados (antes/depois); nunca senhas, tokens ou outros segredos.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.usuario import utcnow

# Tipos de operacao registradas no historico do caso.
OP_CRIACAO = "CRIACAO"
OP_ATUALIZACAO = "ATUALIZACAO"
OP_ARQUIVAMENTO = "ARQUIVAMENTO"


class CasoHistorico(Base):
    __tablename__ = "caso_historicos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    caso_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("casos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    usuario_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    operacao: Mapped[str] = mapped_column(String(20), nullable=False)
    # Ex.: {"titulo": {"antes": "A", "depois": "B"}} - JSON no MySQL e TEXT no
    # SQLite (o SQLAlchemy cuida da diferenca de dialecto).
    dados: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    usuario: Mapped["Usuario | None"] = relationship("Usuario", lazy="selectin")

    def __repr__(self) -> str:
        return f"<CasoHistorico caso={self.caso_id} {self.operacao}>"
