"""Schemas (DTOs) de autenticacao."""

from pydantic import BaseModel, EmailStr, Field

from app.schemas.usuario import UsuarioOut


class LoginRequest(BaseModel):
    """RF01: login por email e senha."""

    email: EmailStr
    senha: str = Field(min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut
