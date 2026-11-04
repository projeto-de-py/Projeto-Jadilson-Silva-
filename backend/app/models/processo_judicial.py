"""Processos judicialmente protocolados vinculados a um Caso (Fase 3).

Um `Caso` representa a demanda juridica do cliente; um `ProcessoJudicial`
representa uma acao formalmente protocolada no Poder Judiciario. O caso
PODE existir sem processo e PODE ter varios processos (1:N).

`numero_processo` e guardado NORMALIZADO (20 digitos, sem mascara) e validado
contra o padrao CNJ (digitos verificadores, modulo 97) - o UNIQUE do banco e
aplicado sobre a forma normalizada.
"""

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.usuario import utcnow


class Instancia(str, enum.Enum):
    """Grau de instancia do processo."""

    PRIMEIRA_INSTANCIA = "PRIMEIRA_INSTANCIA"
    SEGUNDA_INSTANCIA = "SEGUNDA_INSTANCIA"


class StatusProcesso(str, enum.Enum):
    """Situacao atual do processo (BAIXADO/EXTINTO sao encerramentos)."""

    DISTRIBUIDO = "DISTRIBUIDO"
    EM_ANDAMENTO = "EM_ANDAMENTO"
    SUSPENSO = "SUSPENSO"
    AGUARDANDO_SENTENCA = "AGUARDANDO_SENTENCA"
    SENTENCA_PROFERIDA = "SENTENCA_PROFERIDA"
    BAIXADO = "BAIXADO"
    EXTINTO = "EXTINTO"


# Status que representam o encerramento da demanda judicial.
STATUS_ENCERRADOS = (
    StatusProcesso.BAIXADO.value,
    StatusProcesso.EXTINTO.value,
)


class ProcessoJudicial(Base):
    __tablename__ = "processos_judiciais"
    __table_args__ = (
        UniqueConstraint("numero_processo", name="uq_processos_numero"),
        # Valor da causa nunca negativo (regra + restricao no banco).
        CheckConstraint("valor_causa >= 0", name="ck_processos_valor_causa"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Vinculo obrigatorio: todo processo pertence a um caso (N:1).
    caso_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("casos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Normalizado (20 digitos) e unico no banco.
    numero_processo: Mapped[str] = mapped_column(String(20), nullable=False)
    tribunal: Mapped[str | None] = mapped_column(String(120), index=True)
    orgao_julgador: Mapped[str | None] = mapped_column(String(160))  # vara/origem
    comarca: Mapped[str | None] = mapped_column(String(120), index=True)
    instancia: Mapped[str | None] = mapped_column(String(20), index=True)
    classe_processual: Mapped[str | None] = mapped_column(String(80), index=True)
    assunto: Mapped[str | None] = mapped_column(String(200))
    data_distribuicao: Mapped[date | None] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=StatusProcesso.DISTRIBUIDO.value, index=True
    )
    valor_causa: Mapped[float | None] = mapped_column(Numeric(14, 2))
    segredo_justica: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    observacoes: Mapped[str | None] = mapped_column(Text)

    # Arquivamento logico do PROCESSO (distinto do arquivamento do caso).
    arquivado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    arquivado_por: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    arquivado_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    criado_por: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    caso: Mapped["Caso"] = relationship("Caso", back_populates="processos")
    criador: Mapped["Usuario | None"] = relationship(
        "Usuario", foreign_keys=[criado_por], lazy="selectin"
    )

    @property
    def numero_formatado(self) -> str:
        """Exibicao no padrao CNJ (0001234-56.2025.8.26.0100)."""
        n = self.numero_processo or ""
        if len(n) != 20:
            return n
        return (
            f"{n[:7]}-{n[7:9]}.{n[9:13]}.{n[13]}.{n[14:16]}.{n[16:20]}"
        )

    @property
    def criado_por_nome(self) -> str | None:
        return self.criador.nome if self.criador else None

    def __repr__(self) -> str:
        return f"<ProcessoJudicial {self.id} {self.numero_processo} caso={self.caso_id}>"
