"""Model (tabela) Usuario - DER: USUARIO."""

import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Perfil(str, enum.Enum):
    """RF02: dois perfis de acesso."""

    ADMIN = "ADMIN"    # advogado principal (RF04, RF07, RF08)
    PADRAO = "PADRAO"  # demais advogados/funcionarios (RF03)


def utcnow() -> datetime:
    """Data/hora atual em UTC, sem fuso (compativel com MySQL DATETIME)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    perfil: Mapped[str] = mapped_column(
        String(10), nullable=False, default=Perfil.PADRAO.value
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    @property
    def is_admin(self) -> bool:
        return self.perfil == Perfil.ADMIN.value

    def __repr__(self) -> str:
        return f"<Usuario {self.id} {self.email} ({self.perfil})>"
