"""Padrao Repository: persistencia de Andamento. O escopo do usuario e checado no service."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.andamento import Andamento


class AndamentoRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar(self, caso_id: int, limite: int = 200) -> list[Andamento]:
        """Do mais recente para o mais antigo."""
        consulta = (
            select(Andamento)
            .where(Andamento.caso_id == caso_id)
            .order_by(Andamento.ocorrido_em.desc(), Andamento.id.desc())
            .limit(limite)
        )
        return list(self.db.scalars(consulta))

    def buscar(self, caso_id: int, andamento_id: int) -> Andamento | None:
        return self.db.scalar(select(Andamento).where(Andamento.id == andamento_id, Andamento.caso_id == caso_id))

    def chaves_externas(self, caso_id: int) -> set[str]:
        linhas = self.db.scalars(
            select(Andamento.chave_externa).where(Andamento.caso_id == caso_id, Andamento.chave_externa.is_not(None))
        )
        return set(linhas)

    def criar(self, andamento: Andamento) -> Andamento:
        self.db.add(andamento)
        self.db.commit()
        self.db.refresh(andamento)
        return andamento

    def criar_varios(self, andamentos: list[Andamento]) -> None:
        self.db.add_all(andamentos)
        self.db.commit()

    def excluir(self, andamento: Andamento) -> None:
        self.db.delete(andamento)
        self.db.commit()
