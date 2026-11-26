"""Schemas (DTOs) de Documento (Fase 3).

O payload NUNCA aceita `id`, `criado_por`, `criado_em` ou `atualizado_em`: o
autor vem da sessao e as datas sao do servidor. `extra="forbid"` impede que o
cliente falsifique auditoria/ordenacao.

`DocumentoMover` e propositalmente separado: mover de pasta limpa cliente/pasta
quando ausentes e NAO altera `atualizado_em` (nao e edicao de conteudo).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(min_length=1, max_length=200)
    area: str = Field(default="geral", max_length=40)
    tipo: str = Field(default="Documento", max_length=120)
    html: str = Field(default="", max_length=2_000_000)
    # `caso_id` e o vinculo que define o escopo. Sem ele, so o admin cria.
    caso_id: int | None = Field(default=None, gt=0)
    cliente_id: int | None = Field(default=None, gt=0)
    pasta_id: str | None = Field(default=None, max_length=80)


class DocumentoUpdate(BaseModel):
    """Atualizacao parcial de conteudo/vinculos (campos omitidos ficam intactos)."""

    model_config = ConfigDict(extra="forbid")

    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    area: str | None = Field(default=None, max_length=40)
    tipo: str | None = Field(default=None, max_length=120)
    html: str | None = Field(default=None, max_length=2_000_000)
    caso_id: int | None = Field(default=None, gt=0)
    cliente_id: int | None = Field(default=None, gt=0)
    pasta_id: str | None = Field(default=None, max_length=80)


class DocumentoMover(BaseModel):
    """Move para a pasta cliente/personalizada; campos ausentes = voltar à raiz."""

    model_config = ConfigDict(extra="forbid")

    cliente_id: int | None = Field(default=None, gt=0)
    pasta_id: str | None = Field(default=None, max_length=80)


class DocumentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    area: str
    tipo: str
    html: str
    caso_id: int | None = None
    cliente_id: int | None = None
    pasta_id: str | None = None
    criado_por: int | None = None
    criado_em: datetime
    atualizado_em: datetime


class DocumentoPaginaOut(BaseModel):
    itens: list[DocumentoOut]
    total: int
    pagina: int
    limite: int
