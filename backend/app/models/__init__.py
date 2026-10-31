"""Models registrados no metadata para Alembic e create_all."""

from app.models.usuario import Perfil, Usuario
from app.models.cliente import Cliente
from app.models.usuario_caso import UsuarioCaso
from app.models.caso import Caso
from app.models.caso_historico import CasoHistorico
from app.models.andamento import Andamento
from app.models.prazo import Prazo

__all__ = [
    "Perfil",
    "Usuario",
    "Cliente",
    "UsuarioCaso",
    "Caso",
    "CasoHistorico",
    "Andamento",
    "Prazo",
]
