"""Padrao Repository: auditoria das alteracoes de Caso (somente leitura + insert).

Nao existe `atualizar`/`remover`: o historico e imutavel e so e gravado pelos
services (CRIACAO, ATUALIZACAO, ARQUIVAMENTO).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.caso_historico import CasoHistorico


class CasoHistoricoRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar_por_caso(self, caso_id: int) -> list[CasoHistorico]:
        """Entradas do historico, mais recentes primeiro."""
        stmt = (
            select(CasoHistorico)
            .where(CasoHistorico.caso_id == caso_id)
            .order_by(CasoHistorico.criado_em.desc(), CasoHistorico.id.desc())
        )
        return list(self.db.scalars(stmt))

    def registrar(
        self,
        caso_id: int,
        usuario_id: int | None,
        operacao: str,
        dados: dict | None = None,
    ) -> CasoHistorico:
        registro = CasoHistorico(
            caso_id=caso_id, usuario_id=usuario_id, operacao=operacao, dados=dados
        )
        self.db.add(registro)
        self.db.commit()
        self.db.refresh(registro)
        return registro
