"""Model (tabela) Cliente - pessoas (fisicas ou juridicas) atendidas pelo escritorio."""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.usuario import utcnow


class Cliente(Base):
    """Cadastro cadastral unico do cliente (nao duplica dados em outros models).

    Politica de documento ausente: `cpf_cnpj` e anulavel. Como o UNIQUE do
    banco ignora NULL, varios clientes podem ficar sem documento; a unicidade
    e conferida (service + banco) apenas para documentos presentes.
    A coluna guarda somente os digitos: 11 = CPF, 14 = CNPJ.
    """

    __tablename__ = "clientes"
    __table_args__ = (UniqueConstraint("cpf_cnpj", name="uq_clientes_cpf_cnpj"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    cpf_cnpj: Mapped[str | None] = mapped_column(String(14), nullable=True)
    email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    data_nascimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    def __repr__(self) -> str:
        return f"<Cliente {self.id} {self.nome}>"
