"""configuracoes gerais do escritorio

Revision ID: 0013_configuracoes_escritorio
Revises: 0012_notificacoes
Cria a tabela usada por GET/PUT /api/auth/escritorio. O model
ConfiguracaoEscritorio ja existia (defaults aplicados em Python), mas
nunca teve migration - o que fazia o alembic check falhar e obrigava o
seed a criar a tabela fora do controle do Alembic (create_all).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0013_configuracoes_escritorio"
down_revision: Union[str, None] = "0012_notificacoes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "configuracoes_escritorio",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nome", sa.String(length=160), nullable=False),
        sa.Column("oab", sa.String(length=60), nullable=False),
        sa.Column("email", sa.String(length=160), nullable=False),
        sa.Column("telefone", sa.String(length=40), nullable=False),
        sa.Column("endereco", sa.String(length=220), nullable=False),
        sa.Column("assinatura", sa.Text(), nullable=False),
        sa.Column("area_bancario", sa.Boolean(), nullable=False),
        sa.Column("area_previdenciario", sa.Boolean(), nullable=False),
        sa.Column("area_consumidor", sa.Boolean(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("configuracoes_escritorio")
