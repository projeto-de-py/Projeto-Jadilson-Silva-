"""Historico de movimentacoes de um caso.

Um andamento nasce de duas formas (`origem`): registrado a mao pelo advogado (MANUAL) ou
importado do tribunal pelo DataJud (DATAJUD). O importado leva uma `chave_externa` (hash da
movimentacao) para a sincronizacao poder ser repetida sem duplicar nada.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.usuario import utcnow

ORIGEM_MANUAL = "MANUAL"
ORIGEM_DATAJUD = "DATAJUD"


class Andamento(Base):
    __tablename__ = "andamentos"
    # Varios NULL passam no UNIQUE (andamentos manuais); so as chaves do DataJud se repetem.
    __table_args__ = (UniqueConstraint("caso_id", "chave_externa", name="uq_andamento_caso_chave"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    caso_id: Mapped[int] = mapped_column(ForeignKey("casos.id", ondelete="CASCADE"), nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(160), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text)
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, index=True)
    criado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    origem: Mapped[str] = mapped_column(String(20), nullable=False, default=ORIGEM_MANUAL, server_default=ORIGEM_MANUAL)
    chave_externa: Mapped[str | None] = mapped_column(String(64))
    caso: Mapped["Caso"] = relationship(back_populates="andamentos")
