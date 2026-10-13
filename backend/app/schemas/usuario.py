"""Schemas (DTOs) de Usuario."""

from pydantic import BaseModel, ConfigDict, EmailStr


class UsuarioOut(BaseModel):
    """Resposta padrao de usuario - nunca expoe senha_hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: EmailStr
    perfil: str
    ativo: bool


class UsuarioCreate(BaseModel):
    """Cadastro de usuario (apenas Admin)."""

    nome: str
    email: EmailStr
    senha: str
    perfil: str = "PADRAO"
