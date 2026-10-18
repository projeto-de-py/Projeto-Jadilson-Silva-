"""Schemas (DTOs) de Usuario."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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

    nome: str = Field(min_length=1, max_length=120)  # coluna String(120)
    email: EmailStr
    # bcrypt aceita no maximo 72 bytes - limita aqui para nao estourar 500
    senha: str = Field(min_length=6, max_length=72)
    perfil: str = "PADRAO"
