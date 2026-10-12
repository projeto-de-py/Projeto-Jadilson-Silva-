"""RF01: autenticacao - login e usuario logado."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_usuario_repo
from app.models.usuario import Usuario
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.usuario import UsuarioOut
from app.services.auth_service import (
    AuthService,
    ErroAutenticacao,
    UsuarioInativoError,
)

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Autenticar usuario (email + senha)",
)
def login(
    dados: LoginRequest,
    repo: UsuarioRepository = Depends(get_usuario_repo),
):
    service = AuthService(repo)

    try:
        usuario = service.autenticar(dados.email, dados.senha)
    except ErroAutenticacao:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "E-mail ou senha invalidos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except UsuarioInativoError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc))

    token = service.gerar_token(usuario)
    return TokenResponse(access_token=token, usuario=UsuarioOut.model_validate(usuario))


@router.get("/me", response_model=UsuarioOut, summary="Dados do usuario logado")
def me(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    return usuario
