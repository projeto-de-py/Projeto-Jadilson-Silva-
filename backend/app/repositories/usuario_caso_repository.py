"""Padrao Repository: persistencia do relacionamento Usuario <-> Caso."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usuario_caso import UsuarioCaso


class UsuarioCasoRepository:
    def __init__(self, db: Session):
        self.db = db

    def buscar(self, usuario_id: int, caso_id: int) -> UsuarioCaso | None:
        """Linha de permissao (ativa ou revogada) - o UNIQUE impede duplicatas."""
        stmt = select(UsuarioCaso).where(
            UsuarioCaso.usuario_id == usuario_id, UsuarioCaso.caso_id == caso_id
        )
        return self.db.scalar(stmt)

    def listar_por_caso(
        self, caso_id: int, *, incluir_revogados: bool = False
    ) -> list[UsuarioCaso]:
        stmt = select(UsuarioCaso).where(UsuarioCaso.caso_id == caso_id)
        if not incluir_revogados:
            stmt = stmt.where(UsuarioCaso.ativo.is_(True))
        stmt = stmt.order_by(UsuarioCaso.ativo.desc(), UsuarioCaso.usuario_id)
        return list(self.db.scalars(stmt))

    def criar(self, permissao: UsuarioCaso) -> UsuarioCaso:
        self.db.add(permissao)
        self.db.commit()
        self.db.refresh(permissao)
        return permissao

    def atualizar(self, permissao: UsuarioCaso) -> UsuarioCaso:
        """Commit da concessao/revogacao (linha ja carregada na sessao)."""
        self.db.add(permissao)
        self.db.commit()
        self.db.refresh(permissao)
        return permissao
