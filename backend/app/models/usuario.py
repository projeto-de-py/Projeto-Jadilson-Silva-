"""Model (tabela) Usuario - DER: USUARIO."""

import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Perfil(str, enum.Enum):
    """Perfis funcionais (Fase 1).

    O advogado principal NAO possui perfil proprio: e um ADVOGADO que tambem
    detem a permissao administrativa adicional (`Usuario.administrador`).
    """

    ADVOGADO = "ADVOGADO"
    FUNCIONARIO = "FUNCIONARIO"


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
        String(20), nullable=False, default=Perfil.ADVOGADO.value
    )
    # Advogado principal: permissao administrativa adicional (RF02/RF04).
    # Nunca vem de cadastro nem de atualizacao via API - so do provisionamento
    # controlado (seed/admin_email), para impedir escalada de privilegios.
    administrador: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    @property
    def is_admin(self) -> bool:
        """True apenas para o advogado principal (conta provisionada)."""
        return bool(self.administrador)

    def __repr__(self) -> str:
        sufixo = ", admin" if self.administrador else ""
        return f"<Usuario {self.id} {self.email} ({self.perfil}{sufixo})>"
