"""documentos: peças redigidas no escritorio saem do localStorage para o banco"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0015_documentos"
down_revision: Union[str, None] = "0014_andamentos_origem"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documentos",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("area", sa.String(length=40), nullable=False, server_default="geral"),
        sa.Column("tipo", sa.String(length=120), nullable=False, server_default="Documento"),
        # MySQL nao permite DEFAULT em TEXT; o padrao e aplicado no model/service.
        sa.Column("html", sa.Text(), nullable=False),
        sa.Column("caso_id", sa.Integer(), nullable=True),
        sa.Column("cliente_id", sa.Integer(), nullable=True),
        sa.Column("pasta_id", sa.String(length=80), nullable=True),
        sa.Column("criado_por", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["caso_id"], ["casos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["criado_por"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documentos_caso_id", "documentos", ["caso_id"], unique=False)
    op.create_index("ix_documentos_cliente_id", "documentos", ["cliente_id"], unique=False)
    op.create_index("ix_documentos_atualizado_em", "documentos", ["atualizado_em"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_documentos_atualizado_em", table_name="documentos")
    op.drop_index("ix_documentos_cliente_id", table_name="documentos")
    op.drop_index("ix_documentos_caso_id", table_name="documentos")
    op.drop_table("documentos")
