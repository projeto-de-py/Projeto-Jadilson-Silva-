"""Hash de senha (bcrypt) e tokens JWT."""

from datetime import datetime, timedelta, timezone

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

def criar_token(subject: str, perfil: str) -> str:
    """Gera o access token (JWT) com sub, perfil, iat e exp."""
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "perfil": perfil,
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
