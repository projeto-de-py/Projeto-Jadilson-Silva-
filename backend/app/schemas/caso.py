"""Schemas (DTOs) de Caso (Fase 2).

CasoCreate/CasoUpdate sao distintos e usam `extra="forbid"`: campos
administrativos (arquivado, arquivado_por/em, criado_por, id) e de controle de
acesso nunca sao aceitos pelos payloads comuns, entao nao ha como um usuario
alterar privilegios ou arquivar caso pelo PATCH.
"""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.caso import Prioridade, TipoDemanda

# Areas juridicas aceitas na API. Os valores legados ("Civel", "Empresarial",
# "Previdenciario") continuam validos nos registros antigos (coluna String);
# a validacao estrita vale para criacao/atualizacao.
AreaJuridica = Literal["PREVIDENCIARIO", "BANCARIO", "CONSUMIDOR"]

StatusCaso = Literal[
    "NOVO",
    "EM_ANDAMENTO",
    "AGUARDANDO_CLIENTE",
    "AGUARDANDO_SENTENCA",
    "SUSPENSO",
    "CONCLUIDO",
]

TipoDemandaValor = Literal["ADMINISTRATIVA", "EXTRAJUDICIAL", "JUDICIAL"]
PrioridadeValor = Literal["BAIXA", "MEDIA", "ALTA", "URGENTE"]


class CasoCreate(BaseModel):
    """Criacao de caso (advogado autenticado - nunca funcionario).

    `numero_processo` e opcional de proposito: um caso pode ser administrativo
    ou extrajudicial e nao ter numero de processo judicial.
    `responsavel_id` opcional: quando ausente, o proprio operador (que precisa
    ser advogado) assume a responsabilidade.
    """

    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(min_length=3, max_length=200)
    cliente_id: int = Field(gt=0)
    numero_processo: str | None = Field(default=None, max_length=30)
    area: AreaJuridica = "PREVIDENCIARIO"
    tipo_demanda: TipoDemandaValor = TipoDemanda.JUDICIAL.value
    status: StatusCaso = "NOVO"
    prioridade: PrioridadeValor = Prioridade.MEDIA.value
    data_abertura: date | None = None  # padrao: hoje (definido no service)
    responsavel_id: int | None = Field(default=None, gt=0)
    parte_contraria: str | None = Field(default=None, max_length=160)
    tribunal: str | None = Field(default=None, max_length=120)
    vara: str | None = Field(default=None, max_length=160)
    descricao: str | None = Field(default=None, max_length=10000)
    observacoes: str | None = Field(default=None, max_length=10000)


class CasoUpdate(BaseModel):
    """Atualizacao parcial dos dados gerais do caso (admin ou responsavel).

    Nao aceita `arquivado*`, `criado_por` nem `cliente` (espelho do cadastro):
    arquivamento tem rota propria e `cliente` e derivado do `cliente_id`.
    """

    model_config = ConfigDict(extra="forbid")

    titulo: str | None = Field(default=None, min_length=3, max_length=200)
    cliente_id: int | None = Field(default=None, gt=0)
    numero_processo: str | None = Field(default=None, max_length=30)
    area: AreaJuridica | None = None
    tipo_demanda: TipoDemandaValor | None = None
    status: StatusCaso | None = None
    prioridade: PrioridadeValor | None = None
    data_abertura: date | None = None
    responsavel_id: int | None = Field(default=None, gt=0)
    parte_contraria: str | None = Field(default=None, max_length=160)
    tribunal: str | None = Field(default=None, max_length=120)
    vara: str | None = Field(default=None, max_length=160)
    descricao: str | None = Field(default=None, max_length=10000)
    observacoes: str | None = Field(default=None, max_length=10000)


class CasoOut(BaseModel):
    """Resposta padrao de caso (compativel com os campos usados pelo front)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str | None = None
    numero_processo: str | None = None
    cliente: str
    cliente_id: int | None = None
    parte_contraria: str | None = None
    tribunal: str | None = None
    vara: str | None = None
    area: str
    tipo_demanda: str
    status: str
    prioridade: str
    data_abertura: date | None = None
    responsavel_id: int | None = None
    responsavel_nome: str | None = None
    descricao: str | None = None
    observacoes: str | None = None
    arquivado: bool
    arquivado_em: datetime | None = None
    criado_por: int | None = None
    criado_em: datetime
    atualizado_em: datetime


class CasoPaginaOut(BaseModel):
    """Pagina de casos (mesmo formato usado por prazos/clientes)."""

    itens: list[CasoOut]
    total: int
    pagina: int
    limite: int


class HistoricoOut(BaseModel):
    """Entrada do historico de alteracoes do caso (somente leitura)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    operacao: str
    dados: dict[str, Any] | None = None
    usuario_id: int | None = None
    criado_em: datetime
