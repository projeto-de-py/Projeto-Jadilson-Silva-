"""Model (tabela) ConfiguracaoEscritorio - configuracoes gerais do escritorio em SQLite/MySQL."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ConfiguracaoEscritorio(Base):
    __tablename__ = "configuracoes_escritorio"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(
        String(160), nullable=False, default="Jadilson Silva Advocacia"
    )
    oab: Mapped[str] = mapped_column(
        String(60), nullable=False, default="OAB/AL 00.000"
    )
    email: Mapped[str] = mapped_column(
        String(160), nullable=False, default="contato@jadilsonsilva.adv.br"
    )
    telefone: Mapped[str] = mapped_column(
        String(40), nullable=False, default="(82) 3221-0000"
    )
    endereco: Mapped[str] = mapped_column(
        String(220), nullable=False, default="Paulo Afonso/BA"
    )
    assinatura: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="Atenciosamente,\nJadilson Silva Advocacia\nOAB/AL 00.000",
    )
    area_bancario: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    area_previdenciario: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    area_consumidor: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

