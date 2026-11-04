"""Schemas (DTOs) de ProcessoJudicial (Fase 3).

`ProcessoCreate`/`ProcessoUpdate` usam `extra="forbid"` e NUNCA aceitam
`caso_id`, `criado_por` nem `arquivado*`: o vinculo ao caso vem da URL, o
criador e o operador autenticado e o arquivamento tem rota propria. Assim nao
ha como "migrar" um processo para outro caso ou alterar privilegios por
payload comum.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.processo_judicial import Instancia, StatusProcesso

# Situacoes aceitas na API (coluna String: legados continuam validos no banco;
# a validacao estrita vale para criacao/atualizacao).
StatusProcessoValor = Literal[
    "DISTRIBUIDO",
    "EM_ANDAMENTO",
    "SUSPENSO",
    "AGUARDANDO_SENTENCA",
    "SENTENCA_PROFERIDA",
    "BAIXADO",
    "EXTINTO",
]

InstanciaValor = Literal["PRIMEIRA_INSTANCIA", "SEGUNDA_INSTANCIA"]


class ProcessoCreate(BaseModel):
    """Cadastro de processo judicial vinculado a um caso (via URL).

    `numero_processo` e obrigatorio: um processo SEM numero CNJ nao existe de
    fato (e o caso e quem pode nao ter numero). O valor pode vir formatado ou
    so com digitos; o service normaliza e valida os digitos verificadores.
    """

    model_config = ConfigDict(extra="forbid")

    numero_processo: str = Field(min_length=1, max_length=40)
    tribunal: str | None = Field(default=None, max_length=120)
    orgao_julgador: str | None = Field(default=None, max_length=160)
    comarca: str | None = Field(default=None, max_length=120)
    instancia: InstanciaValor | None = None
    classe_processual: str | None = Field(default=None, max_length=80)
    assunto: str | None = Field(default=None, max_length=200)
    data_distribuicao: date | None = None
    status: StatusProcessoValor = StatusProcesso.DISTRIBUIDO.value
    valor_causa: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    segredo_justica: bool = False
    observacoes: str | None = Field(default=None, max_length=10000)


class ProcessoUpdate(BaseModel):
    """Atualizacao parcial dos dados do processo (sem `caso_id`/`criado_por`)."""

    model_config = ConfigDict(extra="forbid")

    numero_processo: str | None = Field(default=None, min_length=1, max_length=40)
    tribunal: str | None = Field(default=None, max_length=120)
    orgao_julgador: str | None = Field(default=None, max_length=160)
    comarca: str | None = Field(default=None, max_length=120)
    instancia: InstanciaValor | None = None
    classe_processual: str | None = Field(default=None, max_length=80)
    assunto: str | None = Field(default=None, max_length=200)
    data_distribuicao: date | None = None
    status: StatusProcessoValor | None = None
    valor_causa: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    segredo_justica: bool | None = None
    observacoes: str | None = Field(default=None, max_length=10000)


class ProcessoStatusUpdate(BaseModel):
    """Mudanca explicita de situacao (encerramento = BAIXADO/EXTINTO)."""

    model_config = ConfigDict(extra="forbid")

    status: StatusProcessoValor


class ProcessoOut(BaseModel):
    """Resposta padrao de processo (numero tambem em formato CNJ)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    caso_id: int
    numero_processo: str
    numero_formatado: str
    tribunal: str | None = None
    orgao_julgador: str | None = None
    comarca: str | None = None
    instancia: str | None = None
    classe_processual: str | None = None
    assunto: str | None = None
    data_distribuicao: date | None = None
    status: str
    valor_causa: Decimal | None = None
    segredo_justica: bool
    observacoes: str | None = None
    arquivado: bool
    arquivado_em: datetime | None = None
    criado_por: int | None = None
    criado_por_nome: str | None = None
    criado_em: datetime
    atualizado_em: datetime


class ProcessoPaginaOut(BaseModel):
    """Pagina de processos (mesmo formato de casos/clientes)."""

    itens: list[ProcessoOut]
    total: int
    pagina: int
    limite: int


class HistoricoProcessoOut(BaseModel):
    """Entrada do historico de um processo (somente leitura)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    operacao: str
    dados: dict[str, Any] | None = None
    usuario_id: int | None = None
    criado_em: datetime
