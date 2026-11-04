"""Schemas (DTOs) de Usuario."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

# Perfis funcionais aceitos na API. Nao existe "ADMIN" como perfil: a conta do
# advogado principal e provisionada fora do cadastro (campo `administrador`).
PerfilEntrada = Literal["ADVOGADO", "FUNCIONARIO"]


class UsuarioOut(BaseModel):
    """Resposta padrao de usuario - nunca expoe senha_hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: EmailStr
    perfil: str
    administrador: bool
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime


class UsuarioCreate(BaseModel):
    """Cadastro de usuario (apenas advogado principal).

    `administrador` NAO e aceito aqui de proposito (extra="forbid"): ninguem
    pode se tornar administrador pelo cadastro - a conta administrativa e
    provisionada pelo processo controlado do seed/config.
    """

    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=120)  # coluna String(120)
    email: EmailStr
    # bcrypt aceita no maximo 72 bytes - limita aqui para nao estourar 500
    senha: str = Field(min_length=6, max_length=72)
    perfil: PerfilEntrada = "ADVOGADO"


class UsuarioUpdate(BaseModel):
    """Ativa/desativar usuario ou trocar o perfil funcional (apenas Admin).

    Somente `ativo` e `perfil` podem ser alterados por aqui: `administrador`,
    `senha` e `email` nao sao campos aceitos (extra="forbid"), de modo que
    ninguem - nem o proprio advogado principal - consegue escalar privilegios
    ou trocar identidade por esta rota.
    """

    model_config = ConfigDict(extra="forbid")

    ativo: bool | None = None
    perfil: PerfilEntrada | None = None

    @model_validator(mode="after")
    def ao_menos_um_campo(self):
        if self.ativo is None and self.perfil is None:
            raise ValueError("Informe ao menos um campo: ativo ou perfil")
        return self
