"""adiciona casos, prazos e andamentos

Revision ID: 0002_casos_prazos
Revises: 0001_cria_usuario
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002_casos_prazos"
down_revision: Union[str, None] = "0001_cria_usuario"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("casos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("numero_processo", sa.String(30), nullable=False),
        sa.Column("cliente", sa.String(160), nullable=False),
        sa.Column("parte_contraria", sa.String(160)),
        sa.Column("tribunal", sa.String(120)), sa.Column("vara", sa.String(160)),
        sa.Column("area", sa.String(80), nullable=False, server_default="Civel"),
        sa.Column("status", sa.String(40), nullable=False, server_default="EM_ANDAMENTO"),
        sa.Column("descricao", sa.Text()), sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("numero_processo", name="uq_casos_numero_processo"))
    op.create_index("ix_casos_cliente", "casos", ["cliente"])
    op.create_index("ix_casos_status", "casos", ["status"])
    op.create_table("andamentos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("caso_id", sa.Integer(), nullable=False), sa.Column("titulo", sa.String(160), nullable=False),
        sa.Column("descricao", sa.Text()), sa.Column("ocorrido_em", sa.DateTime(), nullable=False),
        sa.Column("criado_por_id", sa.Integer()), sa.ForeignKeyConstraint(["caso_id"], ["casos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["criado_por_id"], ["usuarios.id"], ondelete="SET NULL"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_andamentos_caso_id", "andamentos", ["caso_id"])
    op.create_index("ix_andamentos_ocorrido_em", "andamentos", ["ocorrido_em"])
    op.create_table("prazos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False), sa.Column("caso_id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(160), nullable=False), sa.Column("tipo", sa.String(60), nullable=False, server_default="PROCESSUAL"),
        sa.Column("data_limite", sa.Date(), nullable=False), sa.Column("descricao", sa.Text()),
        sa.Column("cumprido", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["caso_id"], ["casos.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_prazos_caso_id", "prazos", ["caso_id"])
    op.create_index("ix_prazos_data_limite", "prazos", ["data_limite"])
    op.create_index("ix_prazos_cumprido", "prazos", ["cumprido"])


def downgrade() -> None:
    op.drop_table("prazos")
    op.drop_table("andamentos")
    op.drop_table("casos")
