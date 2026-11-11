"""notificacoes pessoais"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012_notificacoes"
down_revision: Union[str, None] = "0011_eventos_agenda"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notificacoes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("titulo", sa.String(length=120), nullable=False),
        sa.Column("mensagem", sa.String(length=240), nullable=False),
        sa.Column("link", sa.String(length=300), nullable=False, server_default="/home"),
        sa.Column("severidade", sa.String(length=12), nullable=False, server_default="info"),
        sa.Column("chave_dedupe", sa.String(length=180), nullable=False),
        sa.Column("lida_em", sa.DateTime(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("usuario_id", "chave_dedupe", name="uq_notificacao_usuario_dedupe"),
    )
    op.create_index("ix_notificacoes_usuario_id", "notificacoes", ["usuario_id"])
    op.create_index("ix_notificacoes_criado_em", "notificacoes", ["criado_em"])


def downgrade() -> None:
    # DROP TABLE remove os indices (inclusive os das FKs) junto - no MySQL
    # dropar um index que sustenta FK falha com erro 1553.
    op.drop_table("notificacoes")
