"""Schemas (DTOs) de Cliente."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.validacao import formatar_documento


class ClienteCreate(BaseModel):
    """Cadastro de cliente (apenas advogado principal).

    `cpf_cnpj`, `email`, `telefone` e `data_nascimento` sao opcionais; a
    validacao de CPF/CNPJ (digitos verificadores) e feita no service, onde
    tambem e conferida a unicidade do documento.
    """

    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=160)
    cpf_cnpj: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    telefone: str | None = Field(default=None, max_length=20)
    data_nascimento: date | None = None

    @field_validator("nome")
    @classmethod
    def nome_nao_em_branco(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("Nome e obrigatorio")
        return valor


class ClienteOut(BaseModel):
    """Resposta padrao de cliente - CPF/CNPJ formatado para exibicao."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    cpf_cnpj: str | None = None
    email: str | None = None
    telefone: str | None = None
    data_nascimento: date | None = None
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime

    @field_validator("cpf_cnpj", mode="after")
    @classmethod
    def _formatar_documento(cls, valor: str | None) -> str | None:
        return formatar_documento(valor)


class ClientePaginaOut(BaseModel):
    """Pagina de clientes (mesmo formato de /api/casos)."""

    itens: list[ClienteOut]
    total: int
    pagina: int
    limite: int
