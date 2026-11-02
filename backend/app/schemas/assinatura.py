"""Contratos da assinatura eletronica. Tokens do ZapSign nunca saem na resposta."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ~10 MB de PDF em base64
MAX_PDF_BASE64 = 14_000_000


class AssinaturaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(min_length=1, max_length=200)
    cliente_id: int = Field(ge=1)
    caso_id: int | None = Field(default=None, ge=1)
    pdf_base64: str = Field(min_length=100, max_length=MAX_PDF_BASE64)
    mensagem: str | None = Field(default=None, max_length=500)


class AssinaturaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int | None
    caso_id: int | None
    titulo: str
    status: str
    link_assinatura: str | None
    signatario_nome: str
    criado_em: datetime
    assinado_em: datetime | None
