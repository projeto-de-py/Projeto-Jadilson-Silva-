"""Dependencias compartilhadas (Dependency Injection do FastAPI)."""

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core import security
from app.core.revogados import TokenRevogados
from app.database import get_db
from app.models.usuario import Perfil, Usuario
from app.repositories.usuario_repository import UsuarioRepository

settings = get_settings()


def get_usuario_repo(db: Session = Depends(get_db)) -> UsuarioRepository:
    return UsuarioRepository(db)


def _get_revogados(request: Request) -> TokenRevogados:
    return request.app.state.revogados


def _sub_valido(payload: dict) -> int | None:
    """Extrai o id do usuario a partir do claim `sub`, tolerando tokens malformados.

    Sem isto, um JWT assinado corretamente mas sem `sub` (ou com `sub` nao
    numerico) estourava KeyError/ValueError e virava 500 em vez de 401.
    """
    sub = payload.get("sub")
    try:
        return int(sub)
    except (TypeError, ValueError):
        return None


def get_current_user(
    request: Request,
    token: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
    repo: UsuarioRepository = Depends(get_usuario_repo),
    revogados: TokenRevogados = Depends(_get_revogados),
) -> Usuario:
    """Usuario autenticado a partir do JWT no cookie HttpOnly (RF01).

    O payload tambem e guardado em request.state para o handler de /me
    recuperar o claim `csrf` (o cookie e invisivel para o JavaScript) e para o
    logout recuperar `jti`/`exp` e revogar a sessao.
    """
    if not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Sessao expirada. Entre novamente.",
        )

    payload = security.decodificar_token(token)
    if payload is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Sessao expirada. Entre novamente.",
        )

    if revogados.esta_revogado(payload.get("jti")):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Sessao expirada. Entre novamente.",
        )

    usuario_id = _sub_valido(payload)
    if usuario_id is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Sessao expirada. Entre novamente.",
        )

    usuario = repo.buscar_por_id(usuario_id)
    if usuario is None or not usuario.ativo:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Usuario nao encontrado ou inativo",
        )

    request.state.csrf = payload.get("csrf", "")
    request.state.jti = payload.get("jti")
    request.state.exp = payload.get("exp")
    return usuario


def require_admin(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    """Bloqueia acesso de quem nao for Admin (RF02/RF07/RF08)."""
    if usuario.perfil != Perfil.ADMIN.value:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Acesso restrito ao advogado principal (Admin)",
        )
    return usuario
