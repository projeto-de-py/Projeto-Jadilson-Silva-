"""DTOs da agenda compartilhada."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EventoAgendaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(min_length=1, max_length=120)
    tipo: Literal["AUDIENCIA", "AUDIENCIA_VIRTUAL", "REUNIAO", "CONCILIACAO", "DESPACHO"]
    inicio: datetime
    duracao: int = Field(default=60, ge=15, le=480)
    local: str = Field(default="", max_length=120)
    descricao: str = Field(default="", max_length=2000)
    destinatario_id: int | None = Field(default=None, gt=0)


class EventoAgendaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    tipo: str
    inicio: datetime
    duracao: int
    local: str
    descricao: str
    destinatario_id: int | None
    criado_por_id: int | None


class ContribuidorAgendaOut(BaseModel):
    id: int
    nome: str
