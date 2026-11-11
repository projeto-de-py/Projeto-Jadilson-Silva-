"""Contratos de entrada e saida da IA (Pydantic).

Toda resposta que sai da IA passa por `Sugestao` antes de chegar ao
advogado: o modelo pode errar o formato, o servidor nao.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AreaIA(str, Enum):
    TRABALHISTA = "trabalhista"
    BANCARIO = "bancario"
    PREVIDENCIARIO = "previdenciario"
    GERAL = "geral"


class TarefaIA(str, Enum):
    RESUMO = "resumo"
    CONTESTACAO = "contestacao"
    REVISAR = "revisar"
    CONTINUAR = "continuar"
    LIVRE = "livre"  # qualquer outro pedido escrito pelo advogado


Categoria = Literal["digitacao", "gramatica", "estilo", "juridico", "tom", "risco", "conteudo"]
Severidade = Literal["info", "atencao", "critica"]
TipoSugestao = Literal["Trecho", "Resumo", "Revisão", "Aviso"]

MAX_TEXTO_DOCUMENTO = 60_000
MAX_PEDIDO = 2_000
MAX_TEXTO_ANTES = 3_000


class SugerirRequest(BaseModel):
    """Pedido de sugestoes. `extra=forbid`: campos desconhecidos viram 422."""

    model_config = ConfigDict(extra="forbid")

    tarefa: TarefaIA
    pedido: str = Field(default="", max_length=MAX_PEDIDO)
    area: AreaIA | None = None
    tipo_peca: str | None = Field(default=None, max_length=80)
    caso_id: int | None = Field(default=None, ge=1)
    texto_documento: str = Field(default="", max_length=MAX_TEXTO_DOCUMENTO)
    # Dados do processo vinculado quando ele ainda nao existe no banco (ex.: processo so no front).
    contexto_processo: str = Field(default="", max_length=4_000)


class CompletarRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    texto_antes: str = Field(min_length=1, max_length=MAX_TEXTO_ANTES)
    area: AreaIA | None = None
    caso_id: int | None = Field(default=None, ge=1)


class Sugestao(BaseModel):
    """Uma sugestao da IA, ja validada e com HTML saneado."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    titulo: str = Field(max_length=120)
    previa: str = Field(default="", max_length=400)
    html: str = Field(default="", max_length=20_000)
    tipo: TipoSugestao = "Trecho"
    categoria: Categoria = "conteudo"
    severidade: Severidade = "info"
    trecho: str | None = Field(default=None, max_length=500)
    motivo: str | None = Field(default=None, max_length=500)
    verificar_fonte: bool = False


class RespostaModelo(BaseModel):
    """O que o provedor devolve (antes das checagens de saida)."""

    model_config = ConfigDict(extra="ignore")

    perguntas: list[str] = Field(default_factory=list, max_length=3)
    sugestoes: list[Sugestao] = Field(default_factory=list, max_length=12)


class SugerirResponse(BaseModel):
    sugestoes: list[Sugestao]
    perguntas: list[str] = []
    avisos: list[str] = []
    versao_prompt: str
    provedor: str
    simulado: bool


class CompletarResponse(BaseModel):
    continuacao: str | None
    versao_prompt: str
    simulado: bool


class ArquivoControle(BaseModel):
    nome: str
    tamanho: int
    versao: str


class ControleIAResponse(BaseModel):
    """Visao somente leitura da 'pasta de controle' da IA (para o admin)."""

    provedor: str
    simulado: bool
    perfis: list[ArquivoControle]
    tarefas: list[ArquivoControle]
    exemplos: list[ArquivoControle] = []
