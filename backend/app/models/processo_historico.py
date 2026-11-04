"""Auditoria das alteracoes relevantes de um ProcessoJudicial (Fase 3).

Espelha o padrao de `caso_historicos` (Fase 2) mas e uma tabela PROPRIA: o
historico de um processo e consultado pelo proprio processo, e um registro
nunca deve misturar entidades. `dados` guarda somente os campos alterados
(antes/depois); nunca senhas, tokens ou outros segredos.

Registro imutavel do ponto de vista da API: nao existe endpoint de escrita.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.usuario import utcnow

# Tipos de operacao registradas no historico do processo.
OP_CRIACAO = "CRIACAO"
OP_ATUALIZACAO = "ATUALIZACAO"
OP_MUDANCA_STATUS = "MUDANCA_STATUS"
OP_ARQUIVAMENTO = "ARQUIVAMENTO"


class ProcessoHistorico(Base):
    __tablename__ = "processo_historicos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    processo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("processos_judiciais.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    usuario_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    operacao: Mapped[str] = mapped_column(String(20), nullable=False)
    # Ex.: {"status": {"antes": "EM_ANDAMENTO", "depois": "BAIXADO"}}
    dados: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    usuario: Mapped["Usuario | None"] = relationship("Usuario", lazy="selectin")

    def __repr__(self) -> str:
        return f"<ProcessoHistorico processo={self.processo_id} {self.operacao}>"
