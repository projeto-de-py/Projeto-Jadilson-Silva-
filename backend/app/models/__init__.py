"""Models registrados no metadata para Alembic e create_all."""

from app.models.usuario import Perfil, Usuario
from app.models.cliente import Cliente
from app.models.usuario_caso import UsuarioCaso
from app.models.caso import Caso
from app.models.caso_historico import CasoHistorico
from app.models.processo_judicial import ProcessoJudicial
from app.models.processo_historico import ProcessoHistorico
from app.models.andamento import Andamento
from app.models.prazo import Prazo
from app.models.prazo_historico import PrazoHistorico
from app.models.compromisso import Compromisso
from app.models.compromisso_historico import CompromissoHistorico
from app.models.uso_ia import UsoIA
from app.models.assinatura import Assinatura
from app.models.cobranca import Cobranca
from app.models.evento_webhook import EventoWebhook
from app.models.evento_agenda import EventoAgenda
from app.models.notificacao import Notificacao
from app.models.configuracao_escritorio import ConfiguracaoEscritorio

__all__ = [
    "Perfil",
    "Usuario",
    "Cliente",
    "UsuarioCaso",
    "Caso",
    "CasoHistorico",
    "ProcessoJudicial",
    "ProcessoHistorico",
    "Andamento",
    "Prazo",
    "PrazoHistorico",
    "Compromisso",
    "CompromissoHistorico",
    "UsoIA",
    "Assinatura",
    "Cobranca",
    "EventoWebhook",
    "EventoAgenda",
    "Notificacao",
    "ConfiguracaoEscritorio",
]
