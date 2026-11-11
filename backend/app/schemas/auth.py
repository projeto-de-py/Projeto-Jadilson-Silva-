"""Schemas (DTOs) de autenticacao e configuracoes do escritorio."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field

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


class AlterarSenhaRequest(BaseModel):
    """Troca de senha autenticada."""

    senha_atual: str = Field(min_length=6, max_length=128)
    nova_senha: str = Field(min_length=8, max_length=128)


class ConfiguracaoEscritorioIn(BaseModel):
    """Atualizacao dos dados do escritorio e areas ativas."""

    nome: str | None = Field(default=None, min_length=2, max_length=160)
    oab: str | None = Field(default=None, max_length=60)
    email: str | None = Field(default=None, max_length=160)
    telefone: str | None = Field(default=None, max_length=40)
    endereco: str | None = Field(default=None, max_length=220)
    assinatura: str | None = Field(default=None, max_length=2000)
    area_bancario: bool | None = None
    area_previdenciario: bool | None = None
    area_consumidor: bool | None = None


class ConfiguracaoEscritorioOut(BaseModel):
    """Estado persistido das configuracoes do escritorio."""

    nome: str
    oab: str
    email: str
    telefone: str
    endereco: str
    assinatura: str
    area_bancario: bool
    area_previdenciario: bool
    area_consumidor: bool

    model_config = ConfigDict(from_attributes=True)
