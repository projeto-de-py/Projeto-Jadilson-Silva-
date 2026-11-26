"""Documentos redigidos no escritorio (Fase 3 - migração do localStorage).

Um documento PODE estar vinculado a um caso (`caso_id`) e/ou a um cliente
(`cliente_id`). O vinculo com o caso e a fonte da regra de visibilidade: quem
nao ve o caso nao ve o documento (a mesma regra de processos/andamentos).
Documentos SEM caso pertencem somente ao advogado principal: nao ha como
inferir o escopo de uma peca avulsa.

`pasta_id` e um identificador opaco das pastas personalizadas da UI (que
continuam no navegador); fica no banco apenas para preservar a organizacao
entre dispositivos, sem FK.

`atualizado_em` NAO usa `onupdate`: mover um documento de pasta nao e edicao
de conteudo e nao deve mudar a data de atualizacao exibida na tela. O service
define o valor explicitamente nas operacoes de escrita de conteudo.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.usuario import utcnow


class Documento(Base):
    __tablename__ = "documentos"
    __table_args__ = (
        Index("ix_documentos_caso_id", "caso_id"),
        Index("ix_documentos_cliente_id", "cliente_id"),
        Index("ix_documentos_atualizado_em", "atualizado_em"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    area: Mapped[str] = mapped_column(String(40), nullable=False, default="geral")
    tipo: Mapped[str] = mapped_column(String(120), nullable=False, default="Documento")
    html: Mapped[str] = mapped_column(Text, nullable=False, default="")

    caso_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("casos.id", ondelete="CASCADE"), nullable=True
    )
    cliente_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True
    )
    pasta_id: Mapped[str | None] = mapped_column(String(80), nullable=True)

    criado_por: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )

    def __repr__(self) -> str:
        return f"<Documento {self.id} {self.titulo!r} caso={self.caso_id}>"
