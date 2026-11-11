"""Cobranca de honorarios emitida no Asaas (Pix ou boleto)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.usuario import utcnow

ST_PENDENTE = "PENDENTE"
ST_RECEBIDA = "RECEBIDA"
ST_VENCIDA = "VENCIDA"
ST_CANCELADA = "CANCELADA"

FORMAS = ("PIX", "BOLETO")


class Cobranca(Base):
    __tablename__ = "cobrancas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    caso_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("casos.id", ondelete="SET NULL"), nullable=True, index=True
    )
    asaas_payment_id: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    asaas_installment_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    forma: Mapped[str] = mapped_column(String(10), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    vencimento: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    descricao: Mapped[str | None] = mapped_column(String(200), nullable=True)
    parcela: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    total_parcelas: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ST_PENDENTE, index=True)
    link_fatura: Mapped[str | None] = mapped_column(String(500), nullable=True)
    criado_por: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )
    pago_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Cobranca {self.id} {self.status} {self.valor}>"
