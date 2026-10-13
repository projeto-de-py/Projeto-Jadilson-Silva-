"""cria tabela usuario

Revision ID: 0001_cria_usuario
Revises:
Create Date: 2026-10-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_cria_usuario"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=160), nullable=False),
        sa.Column("senha_hash", sa.String(length=255), nullable=False),
        sa.Column("perfil", sa.String(length=10), nullable=False, server_default="PADRAO"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_usuarios_email"),
    )


def downgrade() -> None:
    op.drop_table("usuarios")
