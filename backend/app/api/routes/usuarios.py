"""Gestao de usuarios - restrita ao advogado principal (RF02)."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_usuario_repo, require_admin
from app.models.usuario import Usuario
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.usuario import UsuarioCreate, UsuarioOut, UsuarioUpdate
from app.services.usuario_service import (
    DadosInvalidosError,
    EmailJaCadastradoError,
    UsuarioNaoEncontradoError,
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
    """Cria apenas usuarios comuns.

    `administrador` nem e aceito no corpo (extra="forbid"): a conta do
    advogado principal e provisionada fora desta API, entao ninguem consegue
    se promover no cadastro.
    """
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


@router.patch(
    "/{usuario_id}",
    response_model=UsuarioOut,
    summary="Ativar/desativar ou trocar o perfil (Admin)",
)
def atualizar(
    usuario_id: int,
    dados: UsuarioUpdate,
    _admin: Usuario = Depends(require_admin),
    repo: UsuarioRepository = Depends(get_usuario_repo),
) -> Usuario:
    """Rota administrativa: o payload nao aceita `administrador`/`senha`/`email`.

    Assim nem o proprio advogado principal altera privilegios pela API, e
    usuarios comuns (sem `require_admin`) recebem 403.
    """
    try:
        return UsuarioService(repo).atualizar(
            usuario_id, ativo=dados.ativo, perfil=dados.perfil
        )
    except UsuarioNaoEncontradoError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    except DadosInvalidosError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
