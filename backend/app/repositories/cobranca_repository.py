"""Padrao Repository: cobrancas de honorarios."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cobranca import Cobranca


class CobrancaRepository:
    def __init__(self, db: Session):
        self.db = db

    def adicionar_varias(self, cobrancas: list[Cobranca]) -> list[Cobranca]:
        self.db.add_all(cobrancas)
        self.db.commit()
        for c in cobrancas:
            self.db.refresh(c)
        return cobrancas

    def buscar_por_id(self, cobranca_id: int) -> Cobranca | None:
        return self.db.get(Cobranca, cobranca_id)

    def buscar_por_pagamento(self, payment_id: str) -> Cobranca | None:
        return self.db.scalar(select(Cobranca).where(Cobranca.asaas_payment_id == payment_id))

    def listar(self, *, cliente_id: int | None = None, status: str | None = None, limite: int = 50) -> list[Cobranca]:
        stmt = select(Cobranca).order_by(Cobranca.vencimento.desc(), Cobranca.id.desc()).limit(limite)
        if cliente_id:
            stmt = stmt.where(Cobranca.cliente_id == cliente_id)
        if status:
            stmt = stmt.where(Cobranca.status == status)
        return list(self.db.scalars(stmt))

    def totais_por_status(self, cliente_id: int) -> dict[str, tuple[int, Decimal]]:
        """{status: (quantidade, soma)} das cobrancas do cliente."""
        stmt = (
            select(Cobranca.status, func.count(Cobranca.id), func.coalesce(func.sum(Cobranca.valor), 0))
            .where(Cobranca.cliente_id == cliente_id)
            .group_by(Cobranca.status)
        )
        return {st: (int(qtd), Decimal(str(soma))) for st, qtd, soma in self.db.execute(stmt)}

    def salvar(self, cobranca: Cobranca) -> Cobranca:
        self.db.add(cobranca)
        self.db.commit()
        self.db.refresh(cobranca)
        return cobranca
