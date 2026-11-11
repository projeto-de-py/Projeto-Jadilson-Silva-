"""Contratos da cobranca de honorarios."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CobrancaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cliente_id: int = Field(ge=1)
    caso_id: int | None = Field(default=None, ge=1)
    valor: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    vencimento: date
    forma: Literal["PIX", "BOLETO"]
    descricao: str | None = Field(default=None, max_length=200)
    parcelas: int = Field(default=1, ge=1, le=24)


class CobrancaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    caso_id: int | None
    forma: str
    valor: Decimal
    vencimento: date
    descricao: str | None
    parcela: int
    total_parcelas: int
    status: str
    link_fatura: str | None
    criado_em: datetime
    pago_em: datetime | None


class ResumoFinanceiroOut(BaseModel):
    cliente_id: int
    pendente: Decimal
    recebido: Decimal
    vencido: Decimal
    cancelado: Decimal
    em_dia: bool  # sem cobranca vencida
