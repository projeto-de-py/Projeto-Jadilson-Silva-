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
]
