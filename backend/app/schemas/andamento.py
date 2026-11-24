"""Schemas (DTOs) de Andamento (Fase 6/RF06 - historico de movimentacoes).

`AndamentoCreate` usa `extra="forbid"` e NUNCA aceita `id`, `criado_por*` nem
`caso_id`: o caso vem da URL (`/api/casos/{caso_id}/andamentos`) e o usuario
responsavel e SEMPRE o operador autenticado, obtido da sessao no service -
nao ha como falsificar auditoria pelo payload.

`ocorrido_em` e tratado como horario LOCAL do escritorio (Brasilia): um
datetime com fuso e convertido, um naive e assumido local; quando ausente,
o service grava o instante atual local (nao ha data futura/padrao inventada).

Integridade historica: nao existe `AndamentoUpdate` e nenhuma rota de
edicao/exclusao - um registro, uma vez gravado, permanece. Correcoes sao feitas
por registro COMPLEMENTAR (novo andamento que retifica o anterior), sem
exclusao fisica do historico.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.tempo import BRASILIA


def _local_brasilia(valor: datetime) -> datetime:
    """Converte para o horario local do escritorio (naive)."""
    if valor.tzinfo is not None:
        return valor.astimezone(BRASILIA).replace(tzinfo=None)
    return valor


class AndamentoCreate(BaseModel):
    """Registro de um andamento no caso da URL (caso_id nao vem no payload)."""

    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(min_length=3, max_length=160)
    descricao: str | None = Field(default=None, max_length=4000)
    ocorrido_em: datetime | None = None

    @model_validator(mode="after")
    def _horario_local(self) -> "AndamentoCreate":
        if self.ocorrido_em is not None:
            self.ocorrido_em = _local_brasilia(self.ocorrido_em)
        return self


class AndamentoOut(BaseModel):
    """Leitura de um andamento (historico imutavel, responsavel sempre visivel)."""

    id: int
    caso_id: int
    titulo: str
    descricao: str | None = None
    ocorrido_em: datetime
    criado_por: int | None = None
    criado_por_nome: str | None = None


class AndamentoPaginaOut(BaseModel):
    """Pagina de andamentos (mesmo formato de casos/prazos/compromissos)."""

    itens: list[AndamentoOut]
    total: int
    pagina: int
    limite: int
