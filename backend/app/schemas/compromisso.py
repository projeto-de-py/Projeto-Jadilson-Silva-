"""Schemas (DTOs) de Compromisso (Fase 4).

`CompromissoCreate`/`CompromissoUpdate` usam `extra="forbid"` e nunca aceitam
`id`, `criado_*` nem `status`: o status nasce AGENDADO e muda apenas pela rota
propria `/status`. `caso_id` nao e alteravel no PATCH.

Horarios sao tratados como horario LOCAL do escritorio (Brasilia): um
datetime com fuso e convertido, um naive e assumido local.
"""

from datetime import datetime, date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.tempo import BRASILIA

TipoCompromissoValor = Literal[
    "AUDIENCIA", "REUNIAO", "ATENDIMENTO", "DILIGENCIA", "OUTRO"
]
StatusCompromissoValor = Literal["AGENDADO", "REALIZADO", "CANCELADO"]


def _local_brasilia(valor: datetime) -> datetime:
    """Converte para o horario local do escritorio (naive)."""
    if valor.tzinfo is not None:
        return valor.astimezone(BRASILIA).replace(tzinfo=None)
    return valor


class CompromissoCreate(BaseModel):
    """Cadastro de compromisso (caso opcional - agenda pessoal do escritorio).

    `responsavel_id` opcional: quando ausente, o responsavel e o operador.
    """

    model_config = ConfigDict(extra="forbid")

    caso_id: int | None = Field(default=None, gt=0)
    processo_id: int | None = Field(default=None, gt=0)
    titulo: str = Field(min_length=3, max_length=160)
    descricao: str | None = Field(default=None, max_length=4000)
    tipo: TipoCompromissoValor
    data_inicio: datetime
    data_fim: datetime
    local: str | None = Field(default=None, max_length=200)
    responsavel_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _horarios_coerentes(self) -> "CompromissoCreate":
        self.data_inicio = _local_brasilia(self.data_inicio)
        self.data_fim = _local_brasilia(self.data_fim)
        if self.data_fim <= self.data_inicio:
            raise ValueError("data_fim deve ser posterior a data_inicio")
        if self.processo_id and not self.caso_id:
            raise ValueError("processo_id exige caso_id")
        return self


class CompromissoUpdate(BaseModel):
    """Atualizacao parcial (PATCH): horarios validados como no cadastro."""

    model_config = ConfigDict(extra="forbid")

    titulo: str | None = Field(default=None, min_length=3, max_length=160)
    descricao: str | None = Field(default=None, max_length=4000)
    tipo: TipoCompromissoValor | None = None
    data_inicio: datetime | None = None
    data_fim: datetime | None = None
    local: str | None = Field(default=None, max_length=200)
    responsavel_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _horarios_locais(self) -> "CompromissoUpdate":
        if self.data_inicio is not None:
            self.data_inicio = _local_brasilia(self.data_inicio)
        if self.data_fim is not None:
            self.data_fim = _local_brasilia(self.data_fim)
        return self


class CompromissoStatusUpdate(BaseModel):
    """Mudanca de status via rota propria (AGENDADO/REALIZADO/CANCELADO)."""

    model_config = ConfigDict(extra="forbid")

    status: StatusCompromissoValor


class CompromissoOut(BaseModel):
    """Leitura de um compromisso (horarios em tempo local do escritorio)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    caso_id: int | None = None
    processo_id: int | None = None
    titulo: str
    descricao: str | None = None
    tipo: str
    data_inicio: datetime
    data_fim: datetime
    local: str | None = None
    responsavel_id: int | None = None
    responsavel_nome: str | None = None
    status: str
    processo_numero: str | None = None
    criado_por: int | None = None
    criado_em: datetime
    atualizado_em: datetime


class CompromissoPaginaOut(BaseModel):
    """Pagina de compromissos (usada tambem pela agenda)."""

    itens: list[CompromissoOut]
    total: int
    pagina: int
    limite: int


class AgendaOut(CompromissoPaginaOut):
    """Recorte temporal da agenda (periodo consultado em horario local)."""

    de: date
    ate: date


class HistoricoCompromissoOut(BaseModel):
    """Entrada do historico de um compromisso (somente leitura, imutavel)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    operacao: str
    dados: dict | None = None
    usuario_id: int | None = None
    criado_em: datetime
