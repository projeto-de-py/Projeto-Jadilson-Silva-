"""Consultas de notificações limitadas sempre ao usuário autenticado."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.notificacao import Notificacao


class NotificacaoRepository:
    def __init__(self, db: Session):
        self.db = db

    def buscar_dedupe(self, usuario_id: int, chave: str) -> Notificacao | None:
        return self.db.scalar(select(Notificacao).where(Notificacao.usuario_id == usuario_id, Notificacao.chave_dedupe == chave))

    def criar(self, notificacao: Notificacao) -> Notificacao:
        self.db.add(notificacao)
        self.db.commit()
        self.db.refresh(notificacao)
        return notificacao

    def listar(self, usuario_id: int, *, pagina: int, limite: int, lidas: bool | None):
        stmt = select(Notificacao).where(Notificacao.usuario_id == usuario_id, Notificacao.tipo != "ARQUIVADA")
        if lidas is not None:
            stmt = stmt.where(Notificacao.lida_em.is_not(None) if lidas else Notificacao.lida_em.is_(None))
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        itens = self.db.scalars(stmt.order_by(Notificacao.criado_em.desc(), Notificacao.id.desc()).offset((pagina - 1) * limite).limit(limite)).all()
        return int(total), list(itens)

    def contar_nao_lidas(self, usuario_id: int) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(Notificacao)
                .where(
                    Notificacao.usuario_id == usuario_id,
                    Notificacao.tipo != "ARQUIVADA",
                    Notificacao.lida_em.is_(None),
                )
            )
            or 0
        )

    def marcar_lida(self, usuario_id: int, notificacao_id: int, quando: datetime) -> Notificacao | None:
        item = self.db.scalar(
            select(Notificacao).where(
                Notificacao.usuario_id == usuario_id,
                Notificacao.id == notificacao_id,
                Notificacao.tipo != "ARQUIVADA",
            )
        )
        if item is None:
            return None
        if item.lida_em is None:
            item.lida_em = quando
            self.db.commit()
        return item

    def marcar_todas_lidas(self, usuario_id: int, quando: datetime) -> int:
        itens = self.db.scalars(
            select(Notificacao).where(
                Notificacao.usuario_id == usuario_id,
                Notificacao.tipo != "ARQUIVADA",
                Notificacao.lida_em.is_(None),
            )
        ).all()
        for item in itens:
            item.lida_em = quando
        self.db.commit()
        return len(itens)

    def limpar_todas(self, usuario_id: int, quando: datetime) -> int:
        itens = self.db.scalars(
            select(Notificacao).where(
                Notificacao.usuario_id == usuario_id,
                Notificacao.tipo != "ARQUIVADA",
            )
        ).all()
        removidas = len(itens)
        for item in itens:
            if item.chave_dedupe.startswith(("prazo:", "audiencia:", "relatorio-semanal:")):
                item.tipo = "ARQUIVADA"
                if item.lida_em is None:
                    item.lida_em = quando
            else:
                self.db.delete(item)
        self.db.commit()
        return removidas
