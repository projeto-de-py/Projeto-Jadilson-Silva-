"""Casos juridicos acompanhados pelo escritorio (evolucao da Fase 2).

Um caso NAO e necessariamente um processo judicial: pode ser uma demanda
administrativa, extrajudicial ou judicial. Por isso `numero_processo` e
OPCIONAL (unico apenas quando preenchido - o UNIQUE do banco ignora NULL).
"""

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.usuario import utcnow


class TipoDemanda(str, enum.Enum):
    """Natureza da demanda (um caso pode nao ser judicial)."""

    ADMINISTRATIVA = "ADMINISTRATIVA"
    EXTRAJUDICIAL = "EXTRAJUDICIAL"
    JUDICIAL = "JUDICIAL"


class Prioridade(str, enum.Enum):
    """Grau de prioridade do caso (usado tambem na ordenacao)."""

    BAIXA = "BAIXA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
    URGENTE = "URGENTE"


# Ordem de exibicao da prioridade (URGENTE primeiro) - usada pelo repository.
ORDEM_PRIORIDADE = {
    Prioridade.URGENTE.value: 4,
    Prioridade.ALTA.value: 3,
    Prioridade.MEDIA.value: 2,
    Prioridade.BAIXA.value: 1,
}


class Caso(Base):
    __tablename__ = "casos"
    __table_args__ = (UniqueConstraint("numero_processo", name="uq_casos_numero_processo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Identificacao do caso (obrigatoria para novos casos - CasoCreate).
    titulo: Mapped[str | None] = mapped_column(String(200), index=True)
    # Opcional: so existe em casos judiciais (unico quando preenchido).
    numero_processo: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Nome do cliente (exibicao/compatibilidade com o frontend existente);
    # em novos casos e um espelho de `cliente_cadastro.nome`.
    cliente: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    # Vinculo com o cadastro de clientes (Fase 1): e por aqui que se descobre
    # "os clientes dos casos que o usuario pode acessar".
    cliente_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    parte_contraria: Mapped[str | None] = mapped_column(String(160))
    tribunal: Mapped[str | None] = mapped_column(String(120))
    vara: Mapped[str | None] = mapped_column(String(160))
    area: Mapped[str] = mapped_column(String(80), nullable=False, default="Civel", index=True)
    # Natureza da demanda: administrativa, extrajudicial ou judicial.
    tipo_demanda: Mapped[str] = mapped_column(
        String(20), nullable=False, default=TipoDemanda.JUDICIAL.value, index=True
    )
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="EM_ANDAMENTO", index=True
    )
    prioridade: Mapped[str] = mapped_column(
        String(10), nullable=False, default=Prioridade.MEDIA.value
    )
    data_abertura: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    # Advogado responsavel pelo caso (perfil ADVOGADO ativo - validado no service).
    responsavel_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True
    )
    descricao: Mapped[str | None] = mapped_column(Text)
    observacoes: Mapped[str | None] = mapped_column(Text)

    # Arquivamento logico (soft delete): preserva historico e relacionamentos.
    arquivado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    arquivado_por: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    arquivado_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Rastreio de quem criou/alterou por ultimo (o historico completo fica em
    # CasoHistorico).
    criado_por: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    cliente_cadastro: Mapped["Cliente | None"] = relationship("Cliente", lazy="selectin")
    responsavel: Mapped["Usuario | None"] = relationship(
        "Usuario", foreign_keys=[responsavel_id], lazy="selectin"
    )
    acessos: Mapped[list["UsuarioCaso"]] = relationship(
        "UsuarioCaso", back_populates="caso", cascade="all, delete-orphan"
    )
    prazos: Mapped[list["Prazo"]] = relationship(back_populates="caso", cascade="all, delete-orphan")
    andamentos: Mapped[list["Andamento"]] = relationship(back_populates="caso", cascade="all, delete-orphan")
    # Compromissos de agenda vinculados a este caso (Fase 4). Os compromissos
    # SEM caso nao estao aqui - nao pertencem a nenhuma demanda.
    compromissos: Mapped[list["Compromisso"]] = relationship(
        back_populates="caso", cascade="all, delete-orphan"
    )
    # Processos judiciais vinculados (Fase 3): um caso pode ter 0..N.
    processos: Mapped[list["ProcessoJudicial"]] = relationship(
        "ProcessoJudicial", back_populates="caso", cascade="all, delete-orphan"
    )

    @property
    def responsavel_nome(self) -> str | None:
        """Nome do responsavel para os DTOs (evita expor o objeto ORM)."""
        return self.responsavel.nome if self.responsavel else None

    def __repr__(self) -> str:
        return f"<Caso {self.id} {self.titulo or self.numero_processo or self.cliente}>"
