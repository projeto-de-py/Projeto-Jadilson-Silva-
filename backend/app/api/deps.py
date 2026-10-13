"""Dependencias compartilhadas (Dependency Injection do FastAPI)."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import security
from app.database import get_db
from app.models.usuario import Perfil, Usuario
from app.repositories.usuario_repository import UsuarioRepository

bearer_scheme = HTTPBearer(auto_error=False)

_UNAUTHORIZED = {"WWW-Authenticate": "Bearer"}


def get_usuario_repo(db: Session = Depends(get_db)) -> UsuarioRepository:
    return UsuarioRepository(db)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    repo: UsuarioRepository = Depends(get_usuario_repo),
) -> Usuario:
    """Usuario autenticado a partir do JWT (RF01)."""
    if credentials is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Nao autenticado",
            headers=_UNAUTHORIZED,
        )

    payload = security.decodificar_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Token invalido ou expirado",
            headers=_UNAUTHORIZED,
        )

    usuario = repo.buscar_por_id(int(payload["sub"]))
    if usuario is None or not usuario.ativo:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Usuario nao encontrado ou inativo",
            headers=_UNAUTHORIZED,
        )
    return usuario


def require_admin(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    """Bloqueia acesso de quem nao for Admin (RF02/RF07/RF08)."""
    if usuario.perfil != Perfil.ADMIN.value:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Acesso restrito ao advogado principal (Admin)",
        )
    return usuario
