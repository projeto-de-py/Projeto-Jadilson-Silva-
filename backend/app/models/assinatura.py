"""Documento enviado para assinatura eletronica (ZapSign).

Guarda so o necessario para acompanhar o fluxo: token do documento no
ZapSign, link do signatario, status e hash do PDF enviado. O PDF em si nao
fica no banco.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.usuario import utcnow

ST_ENVIADO = "ENVIADO"
ST_ASSINADO = "ASSINADO"
ST_RECUSADO = "RECUSADO"
ST_ERRO = "ERRO"


class Assinatura(Base):
    __tablename__ = "assinaturas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    caso_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("casos.id", ondelete="SET NULL"), nullable=True, index=True
    )
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    zapsign_doc_token: Mapped[str | None] = mapped_column(String(80), nullable=True, unique=True)
    link_assinatura: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ST_ENVIADO, index=True)
    signatario_nome: Mapped[str] = mapped_column(String(160), nullable=False)
    signatario_email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    pdf_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    criado_por: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )
    assinado_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Assinatura {self.id} {self.status}>"
