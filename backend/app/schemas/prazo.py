"""Schemas (DTOs) de Prazo (Fase 4).

`PrazoCreate`/`PrazoUpdate` usam `extra="forbid"` e NUNCA aceitam `id`,
`criado_*`, `concluido_*` nem o status final: o criador e sempre o operador
autenticado, o status nasce como PENDENTE e as transicoes de fim de vida
(concluir/reabrir/cancelar) tem rota propria - nao ha como falsificar
auditoria ou "escalar" estado pelo payload.

`caso_id` nao e alteravel no PATCH (o prazo nasce em um caso e ali permanece);
`processo_id` e validado contra o mesmo caso no service. Nao existe campo de
vencido: a situacao e calculada no servidor.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Valores aceitos na API (coluna String: legados continuam validos no banco;
# a validacao estrita vale para criacao/atualizacao).
TipoPrazoValor = Literal[
    "PROCESSUAL", "ADMINISTRATIVO", "CONTRATUAL", "INTERNO", "OUTRO"
]
StatusPrazoValor = Literal[
    "PENDENTE", "EM_ANDAMENTO", "CONCLUIDO", "CANCELADO"
]
# Status aceito no PATCH comum: fim de vida so via /concluir, /reabrir, /cancelar.
StatusEdicaoPrazoValor = Literal["PENDENTE", "EM_ANDAMENTO"]
PrioridadeValor = Literal["BAIXA", "MEDIA", "ALTA", "URGENTE"]
# Classificacao do prazo urgente (calculada com a data local de Brasilia).
SituacaoPrazoValor = Literal["VENCIDO", "HOJE", "PROXIMO"]


class PrazoCreate(BaseModel):
    """Cadastro de prazo vinculado a um caso (caso_id obrigatorio).

    `responsavel_id` opcional: quando ausente, o responsavel passa a ser o
    proprio operador autenticado. Quando presente, o service exige usuario
    ativo com acesso ao caso (nao ha escalada pelo payload).
    """

    model_config = ConfigDict(extra="forbid")

    caso_id: int = Field(gt=0)
    processo_id: int | None = Field(default=None, gt=0)
    titulo: str = Field(min_length=3, max_length=160)
    descricao: str | None = Field(default=None, max_length=4000)
    tipo: TipoPrazoValor = "PROCESSUAL"
    data_inicio: date | None = None
    data_vencimento: date
    prioridade: PrioridadeValor = "MEDIA"
    responsavel_id: int | None = Field(default=None, gt=0)
    observacoes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def _periodo_coerente(self) -> "PrazoCreate":
        if self.data_inicio and self.data_inicio > self.data_vencimento:
            raise ValueError("data_inicio nao pode ser posterior a data_vencimento")
        return self


class PrazoUpdate(BaseModel):
    """Atualizacao parcial (PATCH): so campos editaveis, nada de identidade.

    `status` aceita apenas PENDENTE/EM_ANDAMENTO; CONCLUIDO/CANCELADO exigem
    as rotas proprias. `processo_id` explicitamente nulo desvincula o processo.
    """

    model_config = ConfigDict(extra="forbid")

    titulo: str | None = Field(default=None, min_length=3, max_length=160)
    descricao: str | None = Field(default=None, max_length=4000)
    tipo: TipoPrazoValor | None = None
    data_inicio: date | None = None
    data_vencimento: date | None = None
    status: StatusEdicaoPrazoValor | None = None
    prioridade: PrioridadeValor | None = None
    processo_id: int | None = Field(default=None, gt=0)
    responsavel_id: int | None = Field(default=None, gt=0)
    observacoes: str | None = Field(default=None, max_length=4000)


class PrazoOut(BaseModel):
    """Leitura de um prazo (`vencido` calculado no servidor, nunca armazenado)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    caso_id: int
    processo_id: int | None = None
    titulo: str
    descricao: str | None = None
    tipo: str
    data_inicio: date | None = None
    data_vencimento: date
    status: str
    vencido: bool
    prioridade: str
    responsavel_id: int | None = None
    responsavel_nome: str | None = None
    observacoes: str | None = None
    concluido_em: datetime | None = None
    concluido_por: int | None = None
    criado_por: int | None = None
    criado_em: datetime
    atualizado_em: datetime


class PrazoPaginaOut(BaseModel):
    """Pagina de prazos (mesmo formato de casos/processos)."""

    itens: list[PrazoOut]
    total: int
    pagina: int
    limite: int


class PrazoUrgenteOut(BaseModel):
    """Item do endpoint de urgentes (mantem `numero_processo`/`cliente` do caso)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    caso_id: int
    processo_id: int | None = None
    titulo: str
    tipo: str
    data_vencimento: date
    status: str
    situacao: SituacaoPrazoValor
    vencido: bool
    prioridade: str
    responsavel_id: int | None = None
    responsavel_nome: str | None = None
    numero_processo: str | None = None
    cliente: str | None = None


class PrazoUrgentePaginaOut(BaseModel):
    itens: list[PrazoUrgenteOut]
    total: int
    pagina: int
    limite: int
    dias: int


class HistoricoPrazoOut(BaseModel):
    """Entrada do historico de um prazo (somente leitura, imutavel)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    operacao: str
    dados: dict | None = None
    usuario_id: int | None = None
    criado_em: datetime
