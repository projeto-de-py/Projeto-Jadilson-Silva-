"""Models registrados no metadata para Alembic e create_all."""

from app.models.usuario import Perfil, Usuario
from app.models.caso import Caso
from app.models.andamento import Andamento
from app.models.prazo import Prazo

__all__ = ["Perfil", "Usuario", "Caso", "Andamento", "Prazo"]
