"""Padrao Repository: auditoria das alteracoes de ProcessoJudicial (Fase 3).

Somente leitura + insert: nao existe `atualizar`/`remover` - o historico e
imutavel e so e gravado pelo ProcessoJudicialService.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.processo_historico import ProcessoHistorico


class ProcessoHistoricoRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar_por_processo(self, processo_id: int) -> list[ProcessoHistorico]:
        """Entradas do historico, mais recentes primeiro."""
        stmt = (
            select(ProcessoHistorico)
            .where(ProcessoHistorico.processo_id == processo_id)
            .order_by(ProcessoHistorico.criado_em.desc(), ProcessoHistorico.id.desc())
        )
        return list(self.db.scalars(stmt))

    def registrar(
        self,
        processo_id: int,
        usuario_id: int | None,
        operacao: str,
        dados: dict | None = None,
    ) -> ProcessoHistorico:
        registro = ProcessoHistorico(
            processo_id=processo_id, usuario_id=usuario_id, operacao=operacao, dados=dados
        )
        self.db.add(registro)
        self.db.commit()
        self.db.refresh(registro)
        return registro
