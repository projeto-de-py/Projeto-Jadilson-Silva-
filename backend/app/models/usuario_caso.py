"""Tabela intermediaria Usuario <-> Caso: controle de acesso por caso (Fase 1)."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.usuario import utcnow


class UsuarioCaso(Base):
    """Autorizacao de um usuario a um caso (muitos-para-muitos com permissoes).

    A revogacao e "soft" (`ativo = False` + `revogado_por`/`revogado_em`): a
    linha permanece para preservar a rastreabilidade de quem concedeu e quem
    revogou. O UNIQUE(usuario_id, caso_id) impede associacoes duplicadas -
    conceder de novo reativa a mesma linha em vez de criar outra.
    """

    __tablename__ = "usuario_casos"
    __table_args__ = (UniqueConstraint("usuario_id", "caso_id", name="uq_usuario_caso"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    caso_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("casos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pode_visualizar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    pode_registrar_andamento: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    pode_gerenciar_prazos: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    # Gestao de processos judiciais do caso (Fase 3): criar/editar processos.
    # Funcionario so cadastra processo se o admin conceder esta permissao.
    pode_gerenciar_processos: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    # Gestao de compromissos de AGENDA do caso (Fase 4): criar/editar e mudar
    # status. Permissao PROPRIA - `pode_gerenciar_prazos` nao a concede. Nasce
    # em False (menor privilegio) e so entra na linha quando o admin pedir.
    pode_gerenciar_compromissos: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    concedido_por: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    concedido_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    revogado_por: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    revogado_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    usuario: Mapped["Usuario"] = relationship(
        "Usuario", foreign_keys=[usuario_id], lazy="selectin"
    )
    caso: Mapped["Caso"] = relationship(
        "Caso", back_populates="acessos", foreign_keys=[caso_id]
    )
    concedido_por_usuario: Mapped["Usuario | None"] = relationship(
        "Usuario", foreign_keys=[concedido_por], lazy="selectin"
    )

    def __repr__(self) -> str:
        estado = "ativo" if self.ativo else "revogado"
        return f"<UsuarioCaso u={self.usuario_id} c={self.caso_id} {estado}>"
