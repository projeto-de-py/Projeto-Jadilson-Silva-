"""Consultas a APIs publicas: feriados, CEP, CNPJ, juros do Banco Central e processos no DataJud.

Como esta rota funciona (leia como exemplo do padrao do projeto):

    HTTP  ->  rota (valida a entrada, aplica limite de uso)
          ->  servico (regra do escritorio)          app/services/*
          ->  cliente da API externa                 app/integrations/*

A rota NAO conhece HTTP externo nem cache: so traduz erros (`http_de_integracao`) e
converte dataclasses em schemas de resposta.

Acesso: qualquer usuario logado. Para nao estourar o limite das APIs publicas, cada
usuario tem um teto de consultas por minuto (`CONSULTAS_LIMITE_MINUTO`).
"""

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from app.api.deps import get_current_user
from app.api.erros_integracao import http_de_integracao
from app.config import get_settings
from app.integrations.bcb import BancoCentralClient
from app.integrations.brasilapi import BrasilAPIClient
from app.integrations.datajud import DataJudClient
from app.integrations.erros import IntegracaoErro
from app.models.usuario import Usuario
from app.schemas.consultas import (
    ComparacaoJurosOut,
    CompararJurosIn,
    ConsultaProcessoOut,
    EmpresaOut,
    EnderecoOut,
    FeriadoOut,
    SerieJurosOut,
)
from app.services.calendario_service import CalendarioService
from app.services.juros_service import JurosService
from app.services.processo_externo_service import ProcessoExternoService

router = APIRouter()
settings = get_settings()


# ----------------------------------------------------------------- clientes
# Um cliente por processo (e nao por requisicao): assim o cache de cada API e compartilhado.

@lru_cache
def _brasilapi() -> BrasilAPIClient:
    return BrasilAPIClient(settings.brasilapi_url, timeout=settings.integracao_timeout_segundos)


@lru_cache
def _banco_central() -> BancoCentralClient:
    return BancoCentralClient(settings.bcb_sgs_url, timeout=settings.integracao_timeout_segundos)


@lru_cache
def _datajud() -> DataJudClient:
    chave = settings.datajud_api_key.get_secret_value() if settings.datajud_api_key else None
    return DataJudClient(chave, settings.datajud_api_url, timeout=settings.integracao_timeout_segundos)


# ------------------------------------------------------- dependencias (injecao)
# Os testes trocam estas funcoes via `app.dependency_overrides`.

def get_calendario_service() -> CalendarioService:
    return CalendarioService(_brasilapi())


def get_brasilapi() -> BrasilAPIClient:
    return _brasilapi()


def get_juros_service() -> JurosService:
    return JurosService(_banco_central())


def get_processo_service() -> ProcessoExternoService:
    return ProcessoExternoService(_datajud())


def limitar_consultas(request: Request, usuario: Usuario = Depends(get_current_user)) -> Usuario:
    """Teto de consultas externas por usuario/minuto (protege a cota das APIs publicas)."""
    request.app.state.limiter.check(f"consulta:{usuario.id}", settings.consultas_limite_minuto, 60)
    return usuario


def _com_erros_traduzidos(chamada):
    """Executa `chamada()` e converte falhas de integracao em respostas HTTP."""
    try:
        return chamada()
    except IntegracaoErro as exc:
        raise http_de_integracao(exc)


# ----------------------------------------------------------------- endpoints

@router.get("/feriados/{ano}", response_model=list[FeriadoOut], summary="Feriados nacionais (BrasilAPI)")
def feriados(
    ano: int = Path(ge=1900, le=2199),
    anos: int = Query(1, ge=1, le=5, description="Quantos anos seguidos buscar"),
    _usuario: Usuario = Depends(limitar_consultas),
    servico: CalendarioService = Depends(get_calendario_service),
):
    return _com_erros_traduzidos(lambda: servico.feriados_do_periodo(ano, anos))


@router.get("/cep/{cep}", response_model=EnderecoOut, summary="Endereco de um CEP (BrasilAPI)")
def cep(
    cep: str = Path(min_length=8, max_length=9),
    _usuario: Usuario = Depends(limitar_consultas),
    cliente: BrasilAPIClient = Depends(get_brasilapi),
):
    return _com_erros_traduzidos(lambda: cliente.cep(cep))


@router.get("/cnpj/{cnpj}", response_model=EmpresaOut, summary="Dados publicos de um CNPJ (BrasilAPI)")
def cnpj(
    cnpj: str = Path(min_length=14, max_length=18, description="14 digitos (use so numeros: a barra do CNPJ formatado quebra a URL)"),
    _usuario: Usuario = Depends(limitar_consultas),
    cliente: BrasilAPIClient = Depends(get_brasilapi),
):
    return _com_erros_traduzidos(lambda: cliente.cnpj(cnpj))


@router.get("/juros/series", response_model=list[SerieJurosOut], summary="Series de juros disponiveis (Banco Central)")
def series_de_juros(
    _usuario: Usuario = Depends(get_current_user),
    servico: JurosService = Depends(get_juros_service),
):
    return [SerieJurosOut(slug=s.slug, nome=s.nome, unidade=s.unidade, periodicidade=s.periodicidade) for s in servico.series_disponiveis()]


@router.post("/juros/comparar", response_model=ComparacaoJurosOut, summary="Compara a taxa do contrato com a media do Banco Central")
def comparar_juros(
    dados: CompararJurosIn,
    _usuario: Usuario = Depends(limitar_consultas),
    servico: JurosService = Depends(get_juros_service),
):
    c = _com_erros_traduzidos(lambda: servico.comparar(dados.serie, dados.data_contrato, dados.taxa_contrato_mensal))
    return ComparacaoJurosOut(
        serie=SerieJurosOut(slug=c.serie.slug, nome=c.serie.nome, unidade=c.serie.unidade, periodicidade=c.serie.periodicidade),
        mes_referencia=c.mes_referencia,
        taxa_contrato_mensal=c.taxa_contrato_mensal,
        taxa_media_mensal=c.taxa_media_mensal,
        diferenca_pontos=c.diferenca_pontos,
        razao=c.razao,
        faixa=c.faixa,
        acima_da_media=c.acima_da_media,
        taxa_contrato_anual=c.taxa_contrato_anual,
        taxa_media_anual=c.taxa_media_anual,
        aviso=c.aviso,
    )


@router.get("/processos/{numero}", response_model=ConsultaProcessoOut, summary="Andamentos de um processo (DataJud/CNJ)")
def processo(
    numero: str = Path(min_length=15, max_length=30, description="Numero CNJ, com ou sem pontuacao"),
    _usuario: Usuario = Depends(limitar_consultas),
    servico: ProcessoExternoService = Depends(get_processo_service),
):
    consulta = _com_erros_traduzidos(lambda: servico.consultar(numero))
    return ConsultaProcessoOut(
        numero=consulta.numero,
        tribunal=consulta.tribunal,
        encontrado=consulta.encontrado,
        instancias=[
            {
                "numero": i.numero,
                "tribunal": i.tribunal,
                "grau": i.grau,
                "classe": i.classe,
                "assuntos": list(i.assuntos),
                "orgao_julgador": i.orgao_julgador,
                "data_ajuizamento": i.data_ajuizamento,
                "movimentos": [{"data": m.data, "nome": m.nome, "complemento": m.complemento} for m in i.movimentos],
            }
            for i in consulta.instancias
        ],
    )
