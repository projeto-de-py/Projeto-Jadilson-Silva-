"""Padrao Repository: auditoria das alteracoes de Prazo (Fase 4).

Somente leitura + insert: nao existe `atualizar`/`remover` - o historico e
imutavel e so e gravado pelo PrazoService.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.prazo_historico import PrazoHistorico


class PrazoHistoricoRepository:
    """As escritas NAO commitam: o registro entra na mesma transacao da
    alteracao do prazo (atomicidade) e e confirmado pelo PrazoService."""

    def __init__(self, db: Session):
        self.db = db

    def listar_por_prazo(self, prazo_id: int) -> list[PrazoHistorico]:
        """Entradas do historico, mais recentes primeiro."""
        stmt = (
            select(PrazoHistorico)
            .where(PrazoHistorico.prazo_id == prazo_id)
            .order_by(PrazoHistorico.criado_em.desc(), PrazoHistorico.id.desc())
        )
        return list(self.db.scalars(stmt))

    def registrar(
        self,
        prazo_id: int,
        usuario_id: int | None,
        operacao: str,
        dados: dict | None = None,
    ) -> PrazoHistorico:
        registro = PrazoHistorico(
            prazo_id=prazo_id, usuario_id=usuario_id, operacao=operacao, dados=dados
        )
        self.db.add(registro)
        # flush (nao commit): se este registro falhar, o PrazoService desfaz
        # a alteracao do prazo junto - nunca ha prazo alterado sem auditoria.
        self.db.flush()
        return registro
