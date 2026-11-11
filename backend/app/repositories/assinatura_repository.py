"""Padrao Repository: assinaturas eletronicas."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assinatura import Assinatura


class AssinaturaRepository:
    def __init__(self, db: Session):
        self.db = db

    def criar(self, **dados) -> Assinatura:
        a = Assinatura(**dados)
        self.db.add(a)
        self.db.commit()
        self.db.refresh(a)
        return a

    def buscar_por_id(self, assinatura_id: int) -> Assinatura | None:
        return self.db.get(Assinatura, assinatura_id)

    def buscar_por_token(self, token: str) -> Assinatura | None:
        return self.db.scalar(select(Assinatura).where(Assinatura.zapsign_doc_token == token))

    def listar(self, *, cliente_id: int | None = None, status: str | None = None, limite: int = 50) -> list[Assinatura]:
        stmt = select(Assinatura).order_by(Assinatura.criado_em.desc(), Assinatura.id.desc()).limit(limite)
        if cliente_id:
            stmt = stmt.where(Assinatura.cliente_id == cliente_id)
        if status:
            stmt = stmt.where(Assinatura.status == status)
        return list(self.db.scalars(stmt))

    def salvar(self, assinatura: Assinatura) -> Assinatura:
        self.db.add(assinatura)
        self.db.commit()
        self.db.refresh(assinatura)
        return assinatura
