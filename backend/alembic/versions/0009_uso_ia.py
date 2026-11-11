"""auditoria do uso da IA

Cria `uso_ia`: um registro por solicitacao a IA (usuario, tarefa, area,
provedor, versao do prompt, se foi bloqueada, quantas sugestoes, tokens e
duracao). Nao guarda o texto do pedido nem do documento.

Revision ID: 0009_uso_ia
Revises: 0004_casos_gestao
Create Date: 2026-10-31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009_uso_ia"
down_revision: Union[str, None] = "0007_permissoes_compromissos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "uso_ia",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("tarefa", sa.String(length=20), nullable=False),
        sa.Column("area", sa.String(length=20), nullable=True),
        sa.Column("provedor", sa.String(length=30), nullable=False),
        sa.Column("versao_prompt", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("simulado", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("bloqueado", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("n_sugestoes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_entrada", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_saida", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duracao_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_uso_ia_usuario_id", "uso_ia", ["usuario_id"])
    op.create_index("ix_uso_ia_criado_em", "uso_ia", ["criado_em"])


def downgrade() -> None:
    # DROP TABLE remove os indices (inclusive o da FK usuario_id) junto -
    # no MySQL dropar index que sustenta FK falha com erro 1553.
    op.drop_table("uso_ia")
