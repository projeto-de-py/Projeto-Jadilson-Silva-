"""Formatos de entrada e saída do endpoint de entidades."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

MAX_TEXTO = 20_000


class EntidadesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    texto: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_TEXTO)]


class EntidadeOut(BaseModel):
    tipo: str
    texto: str
    inicio: int
    fim: int
    confianca: float = Field(ge=0, le=1)
    faixa: Literal["alta", "media", "baixa"]


class EntidadesResponse(BaseModel):
    entidades: list[EntidadeOut]
    contagem: dict[str, int]
    versao_modelo: str
    aviso: str = (
        "Reconhecimento automático: pode errar ou deixar passar trechos. "
        "Itens de confiança média ou baixa precisam ser conferidos pelo advogado."
    )
