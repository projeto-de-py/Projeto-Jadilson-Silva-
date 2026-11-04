"""Consulta e gerenciamento de prazos processuais no escopo do usuario."""

from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import get_current_user, get_prazo_repo
from app.models.usuario import Usuario
from app.repositories.prazo_repository import PrazoRepository
from app.services.prazo_service import PrazoNaoEncontradoError, PrazoService

router = APIRouter()


class PrazoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    caso_id: int = Field(gt=0)
    titulo: str = Field(min_length=2, max_length=200)
    data_limite: date
    tipo: str = Field(default="PROCESSUAL", max_length=40)
    descricao: str | None = Field(default=None, max_length=2000)


class PrazoCumpridoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cumprido: bool | None = None


@router.get("", summary="Listar todos os prazos do escopo do usuario")
def listar_prazos(
    pagina: int = Query(1, ge=1),
    limite: int = Query(100, ge=1, le=200),
    _usuario: Usuario = Depends(get_current_user),
    repo: PrazoRepository = Depends(get_prazo_repo),
) -> dict:
    return PrazoService(repo).listar_todos(_usuario, pagina=pagina, limite=limite)


@router.get("/urgentes", summary="Prazos urgentes do escopo do usuario")
def listar_prazos_urgentes(
    dias: int = Query(7, ge=0, le=90),
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    _usuario: Usuario = Depends(get_current_user),
    repo: PrazoRepository = Depends(get_prazo_repo),
) -> dict:
    """Somente prazos de casos que o usuario pode acessar (RF03 no servidor)."""
    return PrazoService(repo).listar_urgentes(
        _usuario, dias=dias, pagina=pagina, limite=limite
    )


@router.post("", status_code=status.HTTP_201_CREATED, summary="Criar prazo em um caso")
def criar_prazo(
    dados: PrazoCreate,
    _usuario: Usuario = Depends(get_current_user),
    repo: PrazoRepository = Depends(get_prazo_repo),
) -> dict:
    try:
        return PrazoService(repo).criar(
            _usuario,
            caso_id=dados.caso_id,
            titulo=dados.titulo,
            data_limite=dados.data_limite,
            tipo=dados.tipo,
            descricao=dados.descricao,
        )
    except PrazoNaoEncontradoError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))


@router.patch("/{prazo_id}/cumprido", summary="Marcar/desmarcar prazo como cumprido")
def alternar_cumprido(
    prazo_id: int,
    dados: PrazoCumpridoIn | None = Body(default=None),
    _usuario: Usuario = Depends(get_current_user),
    repo: PrazoRepository = Depends(get_prazo_repo),
) -> dict:
    try:
        return PrazoService(repo).alternar_cumprido(
            _usuario,
            prazo_id,
            cumprido=dados.cumprido if dados else None,
        )
    except PrazoNaoEncontradoError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))


@router.delete("/{prazo_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Excluir prazo")
def excluir_prazo(
    prazo_id: int,
    _usuario: Usuario = Depends(get_current_user),
    repo: PrazoRepository = Depends(get_prazo_repo),
) -> Response:
    try:
        PrazoService(repo).excluir(_usuario, prazo_id)
    except PrazoNaoEncontradoError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
