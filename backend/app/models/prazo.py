"""Prazos vinculados a casos e, opcionalmente, a processos judiciais (Fase 4).

Evolucao do model legado (Fase 0/1) NA MESMA TABELA - nao existe estrutura
paralela. A migration `0006_prazos_compromissos` faz o backfill reversivel:
- `data_limite`  -> `data_vencimento` (mesmo valor, coluna renomeada);
- `cumprido`     -> `status` ('CONCLUIDO' quando cumprido, senao 'PENDENTE').

Para nao quebrar dados e testes legados (`Prazo(data_limite=...)`,
`prazo.cumprido`), os nomes antigos continuam disponiveis no ORM:
`data_limite` como synonym de `data_vencimento` e `cumprido` como propriedade
derivada do `status` (nunca armazenada em duplicidade).

Regras da Fase 4:
- `vencido` NUNCA e armazenado: e calculado a partir de `data_vencimento` e
  `status` com a data local de Brasilia (`app.core.tempo`);
- NAO ha calculo automatico de prazo processual: a data de vencimento e
  informada manualmente pelo profissional;
- o vinculo com `ProcessoJudicial` e opcional (prazos administrativos/
  extrajudiciais pertencem somente ao caso).
"""

import enum
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.database import Base
from app.models.caso import Prioridade
from app.models.usuario import utcnow


class TipoPrazo(str, enum.Enum):
    """Categoria do prazo (coluna String legado continua aceitando os valores)."""

    PROCESSUAL = "PROCESSUAL"
    ADMINISTRATIVO = "ADMINISTRATIVO"
    CONTRATUAL = "CONTRATUAL"
    INTERNO = "INTERNO"
    OUTRO = "OUTRO"


class StatusPrazo(str, enum.Enum):
    """Estados coerentes do prazo.

    A situacao "vencido" NAO faz parte do armazenamento: ela e derivada de
    `data_vencimento` + `status` (PENDENTE/EM_ANDAMENTO com data passada).
    """

    PENDENTE = "PENDENTE"
    EM_ANDAMENTO = "EM_ANDAMENTO"
    CONCLUIDO = "CONCLUIDO"
    CANCELADO = "CANCELADO"


class Prazo(Base):
    __tablename__ = "prazos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    caso_id: Mapped[int] = mapped_column(
        ForeignKey("casos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Vinculo OPCIONAL com o processo judicial (o processo precisa pertencer
    # ao mesmo caso - validado no service). SET NULL: apagar um processo nunca
    # apaga o prazo do caso.
    processo_id: Mapped[int | None] = mapped_column(
        ForeignKey("processos_judiciais.id", ondelete="SET NULL"), nullable=True, index=True
    )
    titulo: Mapped[str] = mapped_column(String(160), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text)
    tipo: Mapped[str] = mapped_column(
        String(60), nullable=False, default=TipoPrazo.PROCESSUAL.value, index=True
    )
    data_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_vencimento: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # Compatibilidade com o campo legado: mesmos dados, outro nome.
    data_limite = synonym("data_vencimento")

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=StatusPrazo.PENDENTE.value, index=True
    )
    prioridade: Mapped[str] = mapped_column(
        String(10), nullable=False, default=Prioridade.MEDIA.value, index=True
    )
    # Responsavel ativo com acesso ao caso (validado no service); nullable no
    # banco apenas por causa dos registros legados migrados.
    responsavel_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True
    )

    observacoes: Mapped[str | None] = mapped_column(Text)

    # Rastreio (o historico completo fica em PrazoHistorico).
    criado_por: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )
    concluido_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    concluido_por: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )

    caso: Mapped["Caso"] = relationship(back_populates="prazos")
    processo: Mapped["ProcessoJudicial | None"] = relationship(
        "ProcessoJudicial", lazy="selectin"
    )
    responsavel: Mapped["Usuario | None"] = relationship(
        "Usuario", foreign_keys=[responsavel_id], lazy="selectin"
    )

    @hybrid_property
    def cumprido(self) -> bool:
        """Compatibilidade legada: `cumprido` e derivado do `status`."""
        return self.status == StatusPrazo.CONCLUIDO.value

    @cumprido.inplace.setter
    def cumprido(self, valor: bool) -> None:
        self.status = (
            StatusPrazo.CONCLUIDO.value if valor else StatusPrazo.PENDENTE.value
        )

    @cumprido.inplace.expression
    def cumprido(cls):  # noqa: N805 - expressao de classe do hybrid
        return cls.status == StatusPrazo.CONCLUIDO.value

    @property
    def vencido(self) -> bool:
        """Situacao calculada (nunca armazenada): pendente com data passada.

        Usa a data local de Brasilia; concluidos/cancelados nunca aparecem
        como vencidos.
        """
        from app.core.tempo import hoje_brasilia

        if self.status not in (StatusPrazo.PENDENTE.value, StatusPrazo.EM_ANDAMENTO.value):
            return False
        return self.data_vencimento < hoje_brasilia()

    @property
    def responsavel_nome(self) -> str | None:
        """Nome do responsavel para os DTOs (evita expor o objeto ORM)."""
        return self.responsavel.nome if self.responsavel else None

    @property
    def processo_numero(self) -> str | None:
        return self.processo.numero_processo if self.processo else None

    def __repr__(self) -> str:
        return f"<Prazo {self.id} {self.titulo!r} {self.status}>"
