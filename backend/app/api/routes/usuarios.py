"""Gestao de usuarios - restrita ao Admin (RF02)."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_usuario_repo, require_admin
from app.models.usuario import Usuario
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.usuario import UsuarioCreate, UsuarioOut
from app.services.usuario_service import (
    DadosInvalidosError,
    EmailJaCadastradoError,
    UsuarioService,
)

router = APIRouter()


@router.get("", response_model=list[UsuarioOut], summary="Listar usuarios (Admin)")
def listar(
    _admin: Usuario = Depends(require_admin),
    repo: UsuarioRepository = Depends(get_usuario_repo),
) -> list[Usuario]:
    return UsuarioService(repo).listar()


@router.post(
    "",
    response_model=UsuarioOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar usuario (Admin)",
)
def criar(
    dados: UsuarioCreate,
    _admin: Usuario = Depends(require_admin),
    repo: UsuarioRepository = Depends(get_usuario_repo),
) -> Usuario:
    try:
        return UsuarioService(repo).criar(
            nome=dados.nome,
            email=dados.email,
            senha=dados.senha,
            perfil=dados.perfil,
        )
    except EmailJaCadastradoError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    except DadosInvalidosError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
