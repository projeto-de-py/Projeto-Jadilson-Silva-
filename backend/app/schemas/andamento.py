"""Formatos de entrada e saida dos andamentos do caso."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AndamentoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(min_length=2, max_length=160)
    descricao: str | None = Field(default=None, max_length=4000)
    ocorrido_em: date | None = None  # padrao: hoje

    @field_validator("ocorrido_em")
    @classmethod
    def _nao_no_futuro(cls, valor: date | None) -> date | None:
        if valor is not None and valor > date.today():
            raise ValueError("A data do andamento nao pode estar no futuro.")
        return valor


class AndamentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    caso_id: int
    titulo: str
    descricao: str | None
    ocorrido_em: datetime
    origem: str


class SincronizacaoOut(BaseModel):
    numero: str
    tribunal: str
    encontrado: bool
    novos: int
    ja_existentes: int
    mensagem: str
