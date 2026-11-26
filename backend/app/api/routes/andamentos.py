"""Andamentos juridicos - historico de movimentacoes de um caso (Fase 6/RF06).

Sub-recurso montado em `/api/casos`:
- `POST   /api/casos/{caso_id}/andamentos`          registra (201);
- `GET    /api/casos/{caso_id}/andamentos`          lista paginada;
- `GET    /api/casos/{caso_id}/andamentos/{id}`     detalhe.

A autorizacao de leitura herda o escopo do caso (Fase 1): andamento fora do
escopo responde 404, nunca revelando a existencia de casos alheios. A escrita
exige admin, responsavel do caso ou a concessao `pode_registrar_andamento`
(403). NAO EXISTE rota de atualizacao/exclusao: o historico e imutavel -
correcoes acontecem por registro complementar (novo andamento).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status

from app.api.deps import (
    get_andamento_service,
    get_current_user,
)
from app.models.usuario import Usuario
from app.schemas.andamento import (
    AndamentoCreate,
    AndamentoOut,
    AndamentoPaginaOut,
)
from app.services.andamento_service import (
    AndamentoNaoEncontradoError,
    AndamentoSemPermissaoError,
    AndamentoService,
)
from app.services.caso_service import CasoNaoEncontradoError
from app.services.cliente_service import DadosInvalidosError

router = APIRouter()  # prefixo /api/casos


def _mapear_erros_andamento(exc: Exception) -> HTTPException:
    """Traduz erros de negocio do AndamentoService para HTTP."""
    if isinstance(exc, (AndamentoNaoEncontradoError, CasoNaoEncontradoError)):
        return HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, AndamentoSemPermissaoError):
        return HTTPException(http_status.HTTP_403_FORBIDDEN, str(exc))
    if isinstance(exc, DadosInvalidosError):
        return HTTPException(http_status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc))
    raise exc  # nao mapeado: propaga como erro interno


@router.post(
    "/{caso_id}/andamentos",
    response_model=AndamentoOut,
    status_code=http_status.HTTP_201_CREATED,
    summary="Registrar andamento no caso",
)
def criar_andamento(
    caso_id: int,
    dados: AndamentoCreate,
    _usuario: Usuario = Depends(get_current_user),
    service: AndamentoService = Depends(get_andamento_service),
) -> dict:
    """Registra uma movimentacao do caso.

    O responsavel e sempre o operador AUTENTICADO (vem da sessao); o payload
    nao aceita `criado_por`/`caso_id` (extra=forbid). Caso arquivado responde
    422; sem permissao de escrita, 403; caso fora do escopo, 404.
    """
    try:
        return service.criar(caso_id, dados, _usuario)
    except Exception as exc:  # noqa: BLE001 - mapeado abaixo
        raise _mapear_erros_andamento(exc)


@router.get(
    "/{caso_id}/andamentos",
    response_model=AndamentoPaginaOut,
    summary="Andamentos do caso (escopo do usuario, paginado no banco)",
)
def listar_andamentos(
    caso_id: int,
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    ordem: str = Query(
        "desc",
        pattern="^(asc|desc)$",
        description="Cronologia: desc = mais recente primeiro (padrao da UI)",
    ),
    _usuario: Usuario = Depends(get_current_user),
    service: AndamentoService = Depends(get_andamento_service),
) -> dict:
    """Lista cronologica de movimentacoes; 404 se o caso estiver fora do escopo."""
    try:
        return service.listar(
            caso_id, _usuario, pagina=pagina, limite=limite, ordem=ordem
        )
    except CasoNaoEncontradoError as exc:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))


@router.get(
    "/{caso_id}/andamentos/{andamento_id}",
    response_model=AndamentoOut,
    summary="Detalhe do andamento (404 fora do escopo)",
)
def buscar_andamento(
    caso_id: int,
    andamento_id: int,
    _usuario: Usuario = Depends(get_current_user),
    service: AndamentoService = Depends(get_andamento_service),
) -> dict:
    try:
        return service.buscar(caso_id, andamento_id, _usuario)
    except Exception as exc:  # noqa: BLE001 - mapeado abaixo
        raise _mapear_erros_andamento(exc)
