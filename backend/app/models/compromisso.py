"""Compromissos de agenda do escritorio (Fase 4).

Entidade PROPRIA: audiencias, reunioes e atendimentos NUNCA sao representados
como `Prazo` - prazo juridico e compromisso de agenda sao coisas distintas.

Horarios: `data_inicio`/`data_fim` guardam o HORARIO LOCAL do escritorio
(Brasilia, naive) porque a agenda e lida em horario de trabalho; os campos de
auditoria (`criado_em` etc.) continuam em UTC via `utcnow()`.

`caso_id` e opcional: um compromisso pode nao estar ligado a nenhuma demanda
(nesses casos, somente o administrador o enxerga - ver
`escopo.condicao_compromisso_visivel`).
"""

import enum
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.usuario import utcnow


class TipoCompromisso(str, enum.Enum):
    AUDIENCIA = "AUDIENCIA"
    REUNIAO = "REUNIAO"
    ATENDIMENTO = "ATENDIMENTO"
    DILIGENCIA = "DILIGENCIA"
    OUTRO = "OUTRO"


class StatusCompromisso(str, enum.Enum):
    AGENDADO = "AGENDADO"
    REALIZADO = "REALIZADO"
    CANCELADO = "CANCELADO"


class Compromisso(Base):
    __tablename__ = "compromissos"
    __table_args__ = (
        # data_fim sempre posterior a data_inicio (validado tambem no schema).
        CheckConstraint("data_fim > data_inicio", name="ck_compromissos_periodo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # OPCIONAL: compromissos sem caso nao dependem de demanda nenhuma.
    caso_id: Mapped[int | None] = mapped_column(
        ForeignKey("casos.id", ondelete="CASCADE"), nullable=True, index=True
    )
    # Opcional; se preenchido, precisa pertencer ao mesmo caso (service).
    processo_id: Mapped[int | None] = mapped_column(
        ForeignKey("processos_judiciais.id", ondelete="SET NULL"), nullable=True, index=True
    )
    titulo: Mapped[str] = mapped_column(String(160), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text)
    tipo: Mapped[str] = mapped_column(
        String(30), nullable=False, default=TipoCompromisso.OUTRO.value, index=True
    )
    # Horario local do escritorio (naive, Brasilia - ver docstring).
    data_inicio: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    data_fim: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    local: Mapped[str | None] = mapped_column(String(200))
    responsavel_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=StatusCompromisso.AGENDADO.value, index=True
    )

    # Rastreio (o historico completo fica em CompromissoHistorico).
    criado_por: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    caso: Mapped["Caso | None"] = relationship("Caso", back_populates="compromissos")
    processo: Mapped["ProcessoJudicial | None"] = relationship(
        "ProcessoJudicial", lazy="selectin"
    )
    responsavel: Mapped["Usuario | None"] = relationship(
        "Usuario", foreign_keys=[responsavel_id], lazy="selectin"
    )

    @property
    def responsavel_nome(self) -> str | None:
        return self.responsavel.nome if self.responsavel else None

    @property
    def processo_numero(self) -> str | None:
        return self.processo.numero_processo if self.processo else None

    def __repr__(self) -> str:
        return f"<Compromisso {self.id} {self.titulo!r} {self.status}>"
