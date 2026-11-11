"""Padrao Repository: auditoria das alteracoes de Compromisso (Fase 4).

Somente leitura + insert: nao existe `atualizar`/`remover` - o historico e
imutavel e so e gravado pelo CompromissoService.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.compromisso_historico import CompromissoHistorico


class CompromissoHistoricoRepository:
    """As escritas NAO commitam: o registro entra na mesma transacao da
    alteracao do compromisso (atomicidade) e e confirmado pelo Service."""

    def __init__(self, db: Session):
        self.db = db

    def listar_por_compromisso(self, compromisso_id: int) -> list[CompromissoHistorico]:
        """Entradas do historico, mais recentes primeiro."""
        stmt = (
            select(CompromissoHistorico)
            .where(CompromissoHistorico.compromisso_id == compromisso_id)
            .order_by(
                CompromissoHistorico.criado_em.desc(),
                CompromissoHistorico.id.desc(),
            )
        )
        return list(self.db.scalars(stmt))

    def registrar(
        self,
        compromisso_id: int,
        usuario_id: int | None,
        operacao: str,
        dados: dict | None = None,
    ) -> CompromissoHistorico:
        registro = CompromissoHistorico(
            compromisso_id=compromisso_id,
            usuario_id=usuario_id,
            operacao=operacao,
            dados=dados,
        )
        self.db.add(registro)
        # flush (nao commit): se este registro falhar, o CompromissoService
        # desfaz a alteracao junto - nunca ha alteracao sem auditoria.
        self.db.flush()
        return registro
