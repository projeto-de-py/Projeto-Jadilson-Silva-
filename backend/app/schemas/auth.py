"""Schemas (DTOs) de autenticacao."""

from pydantic import BaseModel, EmailStr, Field

from app.schemas.usuario import UsuarioOut


class LoginRequest(BaseModel):
    """RF01: login por email e senha."""

    email: EmailStr
    senha: str = Field(min_length=6, max_length=128)


class LoginResponse(BaseModel):
    """Resposta do login/me.

    O JWT NUNCA aparece aqui - ele vai em cookie HttpOnly (inacessivel ao
    JavaScript). O `csrf_token` e o claim embutido no JWT, devolvido ao front
    para que ele o envie no header X-CSRF-Token nas requisicoes mutantes.
    """

    usuario: UsuarioOut
    csrf_token: str
