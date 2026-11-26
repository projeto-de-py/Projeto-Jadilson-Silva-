"""Documentos do escritorio (Fase 3 - antes no localStorage do navegador).

Leitura e escrita herdam o escopo do caso: documento fora do escopo responde
404, nunca 403 (nao revela existencia). O autor e sempre o usuario da sessao
 e as datas sao do servidor — o payload nao pode falsificar auditoria.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status

from app.api.deps import get_current_user, get_documento_service
from app.models.documento import Documento
from app.models.usuario import Usuario
from app.schemas.documento import (
    DocumentoCreate,
    DocumentoMover,
    DocumentoOut,
    DocumentoPaginaOut,
    DocumentoUpdate,
)
from app.services.caso_service import CasoNaoEncontradoError
from app.services.cliente_service import DadosInvalidosError
from app.services.documento_service import (
    DocumentoNaoEncontradoError,
    DocumentoService,
    DocumentoSemPermissaoError,
)

router = APIRouter()  # prefixo /api/documentos


def _mapear_erro(exc: Exception) -> HTTPException:
    if isinstance(exc, (DocumentoNaoEncontradoError, CasoNaoEncontradoError)):
        return HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, DocumentoSemPermissaoError):
        return HTTPException(http_status.HTTP_403_FORBIDDEN, str(exc))
    if isinstance(exc, DadosInvalidosError):
        return HTTPException(http_status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc))
    raise exc


@router.get(
    "",
    response_model=DocumentoPaginaOut,
    summary="Listar documentos (escopo do caso, paginado no banco)",
)
def listar_documentos(
    q: str | None = Query(None, min_length=1, max_length=200),
    caso_id: int | None = Query(None, gt=0),
    cliente_id: int | None = Query(None, gt=0),
    area: str | None = Query(None, max_length=40),
    pagina: int = Query(1, ge=1),
    # A tela carrega a carteira de uma vez; 200 cobre a rotina do escritorio.
    limite: int = Query(20, ge=1, le=500),
    _usuario: Usuario = Depends(get_current_user),
    service: DocumentoService = Depends(get_documento_service),
) -> DocumentoPaginaOut:
    return service.listar(
        _usuario,
        q=q,
        caso_id=caso_id,
        cliente_id=cliente_id,
        area=area,
        pagina=pagina,
        limite=limite,
    )


@router.post(
    "",
    response_model=DocumentoOut,
    status_code=http_status.HTTP_201_CREATED,
    summary="Criar documento (vinculado ao caso, quando informado)",
)
def criar_documento(
    dados: DocumentoCreate,
    operador: Usuario = Depends(get_current_user),
    service: DocumentoService = Depends(get_documento_service),
) -> Documento:
    try:
        return service.criar(dados, operador)
    except Exception as exc:  # noqa: BLE001 - mapeado abaixo
        raise _mapear_erro(exc)


@router.get(
    "/{documento_id}",
    response_model=DocumentoOut,
    summary="Detalhe do documento (404 fora do escopo)",
)
def buscar_documento(
    documento_id: int,
    _usuario: Usuario = Depends(get_current_user),
    service: DocumentoService = Depends(get_documento_service),
) -> Documento:
    try:
        return service.buscar(documento_id, _usuario)
    except DocumentoNaoEncontradoError as exc:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))


@router.patch(
    "/{documento_id}",
    response_model=DocumentoOut,
    summary="Atualizar conteudo/vinculos do documento",
)
def atualizar_documento(
    documento_id: int,
    dados: DocumentoUpdate,
    operador: Usuario = Depends(get_current_user),
    service: DocumentoService = Depends(get_documento_service),
) -> Documento:
    try:
        return service.atualizar(documento_id, dados, operador)
    except Exception as exc:  # noqa: BLE001 - mapeado abaixo
        raise _mapear_erro(exc)


@router.patch(
    "/{documento_id}/mover",
    response_model=DocumentoOut,
    summary="Mover documento de pasta (sem alterar a data de edicao)",
)
def mover_documento(
    documento_id: int,
    dados: DocumentoMover,
    operador: Usuario = Depends(get_current_user),
    service: DocumentoService = Depends(get_documento_service),
) -> Documento:
    try:
        return service.mover(documento_id, dados, operador)
    except Exception as exc:  # noqa: BLE001 - mapeado abaixo
        raise _mapear_erro(exc)


@router.delete(
    "/{documento_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="Excluir documento",
)
def excluir_documento(
    documento_id: int,
    operador: Usuario = Depends(get_current_user),
    service: DocumentoService = Depends(get_documento_service),
) -> None:
    try:
        service.excluir(documento_id, operador)
    except Exception as exc:  # noqa: BLE001 - mapeado abaixo
        raise _mapear_erro(exc)
