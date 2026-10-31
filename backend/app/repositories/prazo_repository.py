"""Padrao Repository: consultas de Prazo (com o escopo de acesso do usuario)."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.caso import Caso
from app.models.prazo import Prazo
from app.models.usuario import Usuario
from app.repositories.escopo import condicao_prazo_visivel


class PrazoRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar_urgentes(
        self,
        *,
        usuario: Usuario,
        ate: date,
        pagina: int = 1,
        limite: int = 20,
    ) -> tuple[int, list[tuple[Prazo, str, str]]]:
        """Prazos nao cumpridos ate a data limite, restritos ao escopo do usuario."""
        filtros = [
            Prazo.cumprido.is_(False),
            Prazo.data_limite <= ate,
            condicao_prazo_visivel(usuario),
        ]
        total = self.db.scalar(select(func.count()).select_from(Prazo).where(*filtros)) or 0
        rows = (
            self.db.execute(
                select(Prazo, Caso.numero_processo, Caso.cliente)
                .join(Caso)
                .where(*filtros)
                .order_by(Prazo.data_limite, Prazo.id)
                .offset((pagina - 1) * limite)
                .limit(limite)
            )
            .all()
        )
        return int(total), [(prazo, numero, cliente) for prazo, numero, cliente in rows]
