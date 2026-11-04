"""Padrao Repository: consultas e persistencia de Prazo (com escopo do usuario)."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.caso import Caso
from app.models.prazo import Prazo
from app.models.usuario import Usuario
from app.repositories.escopo import condicao_caso_visivel, condicao_prazo_visivel


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
    ) -> tuple[int, list[tuple[Prazo, str | None, str]]]:
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

    def listar_todos(
        self,
        *,
        usuario: Usuario,
        pagina: int = 1,
        limite: int = 100,
    ) -> tuple[int, list[tuple[Prazo, Caso]]]:
        """Lista todos os prazos (abertos e cumpridos) dos casos visiveis ao usuario."""
        filtros = [condicao_prazo_visivel(usuario)]
        total = self.db.scalar(select(func.count()).select_from(Prazo).where(*filtros)) or 0
        rows = (
            self.db.execute(
                select(Prazo, Caso)
                .join(Caso)
                .where(*filtros)
                .order_by(Prazo.cumprido, Prazo.data_limite, Prazo.id)
                .offset((pagina - 1) * limite)
                .limit(limite)
            )
            .all()
        )
        return int(total), [(prazo, caso) for prazo, caso in rows]

    def buscar_caso_visivel(self, caso_id: int, usuario: Usuario) -> Caso | None:
        return self.db.scalar(
            select(Caso).where(Caso.id == caso_id, condicao_caso_visivel(usuario))
        )

    def buscar_visivel(self, prazo_id: int, usuario: Usuario) -> tuple[Prazo, Caso] | None:
        row = self.db.execute(
            select(Prazo, Caso)
            .join(Caso)
            .where(Prazo.id == prazo_id, condicao_prazo_visivel(usuario))
        ).first()
        if row is None:
            return None
        return row[0], row[1]

    def criar(self, prazo: Prazo) -> Prazo:
        self.db.add(prazo)
        self.db.commit()
        self.db.refresh(prazo)
        return prazo

    def salvar(self, prazo: Prazo) -> Prazo:
        self.db.add(prazo)
        self.db.commit()
        self.db.refresh(prazo)
        return prazo

    def excluir(self, prazo: Prazo) -> None:
        self.db.delete(prazo)
        self.db.commit()
