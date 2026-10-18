"""Hash de senha (bcrypt) e tokens JWT."""

from datetime import datetime, timedelta, timezone
import secrets

import bcrypt
import jwt

from app.config import get_settings

settings = get_settings()


# ---------------------------------------------------------------- senhas

def hash_senha(senha: str) -> str:
    """Gera o hash bcrypt da senha (nunca armazenar a senha pura - RNF01)."""
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Confere a senha digitada com o hash salvo."""
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ------------------------------------------------------------------ JWT

def criar_token(subject: str, perfil: str, csrf: str) -> str:
    """Gera o access token (JWT) com sub, perfil, csrf, jti, iat e exp.

    O claim `csrf` embute o token sincronizador: o front o recebe no login/me
    e o devolve no header X-CSRF-Token em requisicoes mutantes. Como o JWT vai
    em cookie HttpOnly, o browser envia a sessao sozinho e o CSRF impede que
    um site malicioso consiga forcar acoes em nome do usuario.

    O claim `jti` identifica unicamente a sessao e permite revogar o token no
    logout (ver core/revogados.py) - sem ele, um token roubado continuaria
    valido ate expirar mesmo apos o usuario deslogar.
    """
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "perfil": perfil,
        "csrf": csrf,
        "jti": secrets.token_urlsafe(16),
        "iat": agora,
        "exp": agora + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decodificar_token(token: str) -> dict | None:
    """Valida a assinatura/expiracao e devolve o payload (ou None se invalido)."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
