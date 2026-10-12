"""Padrao Repository: isola o acesso a dados do Usuario (regras nao tocam no SQL)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.usuario import Usuario


class UsuarioRepository:
    def __init__(self, db: Session):
        self.db = db

    def buscar_por_email(self, email: str) -> Usuario | None:
        stmt = select(Usuario).where(Usuario.email == email)
        return self.db.scalar(stmt)

    def buscar_por_id(self, usuario_id: int) -> Usuario | None:
        return self.db.get(Usuario, usuario_id)

    def listar(self) -> list[Usuario]:
        stmt = select(Usuario).order_by(Usuario.nome)
        return list(self.db.scalars(stmt))

    def contar(self) -> int:
        return self.db.scalar(select(func.count()).select_from(Usuario)) or 0

    def criar(self, usuario: Usuario) -> Usuario:
        self.db.add(usuario)
        self.db.commit()
        self.db.refresh(usuario)
        return usuario
