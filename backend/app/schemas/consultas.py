"""Contratos das consultas externas (feriados, CEP, CNPJ, juros do BC, DataJud)."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class FeriadoOut(BaseModel):
    data: date
    nome: str
    tipo: str


class EnderecoOut(BaseModel):
    cep: str
    estado: str
    cidade: str
    bairro: str
    rua: str


class EmpresaOut(BaseModel):
    cnpj: str
    razao_social: str
    nome_fantasia: str
    situacao: str
    municipio: str
    uf: str


class SerieJurosOut(BaseModel):
    slug: str
    nome: str
    unidade: str
    periodicidade: str


class CompararJurosIn(BaseModel):
    """Entrada da comparacao. `extra=forbid`: campo desconhecido vira 422."""

    model_config = ConfigDict(extra="forbid")

    serie: str = Field(min_length=1, max_length=60)
    data_contrato: date
    taxa_contrato_mensal: Decimal = Field(gt=0, le=100, max_digits=7, decimal_places=4, description="% ao mes, ex.: 5.2")


class ComparacaoJurosOut(BaseModel):
    serie: SerieJurosOut
    mes_referencia: date
    taxa_contrato_mensal: Decimal
    taxa_media_mensal: Decimal
    diferenca_pontos: Decimal
    razao: Decimal
    faixa: str
    acima_da_media: bool
    taxa_contrato_anual: Decimal
    taxa_media_anual: Decimal
    aviso: str
    fonte: str = "Banco Central do Brasil - SGS"


class MovimentoOut(BaseModel):
    data: datetime | None
    nome: str
    complemento: str


class ProcessoExternoOut(BaseModel):
    numero: str
    tribunal: str
    grau: str
    classe: str
    assuntos: list[str]
    orgao_julgador: str
    data_ajuizamento: datetime | None
    movimentos: list[MovimentoOut]


class ConsultaProcessoOut(BaseModel):
    numero: str
    tribunal: str
    encontrado: bool
    instancias: list[ProcessoExternoOut]
    fonte: str = "DataJud - CNJ"
    aviso: str = "Dados e movimentações do DataJud (sem inteiro teor). Processos em segredo de justiça não aparecem."
