"""eventos compartilhados da agenda"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_eventos_agenda"
down_revision: Union[str, None] = "0006_assinaturas_financeiro"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "eventos_agenda",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("titulo", sa.String(length=120), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("inicio", sa.DateTime(), nullable=False),
        sa.Column("duracao", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("local", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("descricao", sa.Text(), nullable=False, server_default=""),
        sa.Column("destinatario_id", sa.Integer(), nullable=True),
        sa.Column("criado_por_id", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["destinatario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["criado_por_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eventos_agenda_inicio", "eventos_agenda", ["inicio"])
    op.create_index("ix_eventos_agenda_destinatario_id", "eventos_agenda", ["destinatario_id"])
    op.create_index("ix_eventos_agenda_criado_por_id", "eventos_agenda", ["criado_por_id"])


def downgrade() -> None:
    op.drop_index("ix_eventos_agenda_criado_por_id", table_name="eventos_agenda")
    op.drop_index("ix_eventos_agenda_destinatario_id", table_name="eventos_agenda")
    op.drop_index("ix_eventos_agenda_inicio", table_name="eventos_agenda")
    op.drop_table("eventos_agenda")
