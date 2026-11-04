"""Contratos da API de notificações."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class NotificacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    usuario_id: int
    tipo: str
    titulo: str
    mensagem: str
    link: str
    severidade: Literal["info", "atencao", "critica"]
    lida_em: datetime | None
    criado_em: datetime


class NotificacaoPaginaOut(BaseModel):
    itens: list[NotificacaoOut]
    total: int
    pagina: int
    limite: int


class ContagemNotificacaoOut(BaseModel):
    nao_lidas: int


TipoNotificacaoConfig = Literal[
    "prazoHoje",
    "prazo3dias",
    "audiencias",
    "novosClientes",
    "relatorioSemanal",
]


class TesteNotificacaoIn(BaseModel):
    tipo: TipoNotificacaoConfig | None = None
    tipos: list[TipoNotificacaoConfig] | None = None


class TesteNotificacaoOut(BaseModel):
    criadas: int
    itens: list[NotificacaoOut]
