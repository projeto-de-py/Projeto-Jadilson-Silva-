"""assinatura eletronica (ZapSign) e cobranca de honorarios (Asaas)

- assinaturas: documentos enviados para assinar e o status de cada um;
- cobrancas: cobrancas Pix/boleto emitidas no Asaas e o status financeiro;
- eventos_webhook: eventos ja processados (idempotencia);
- clientes.asaas_customer_id: id do cliente no Asaas (evita cadastrar duas vezes).

Revision ID: 0010_assinaturas_financeiro
Revises: 0009_uso_ia
Create Date: 2026-11-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010_assinaturas_financeiro"
down_revision: Union[str, None] = "0009_uso_ia"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("clientes") as batch_op:
        batch_op.add_column(sa.Column("asaas_customer_id", sa.String(length=40), nullable=True))
        batch_op.create_unique_constraint("uq_clientes_asaas_customer_id", ["asaas_customer_id"])

    op.create_table(
        "assinaturas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=True),
        sa.Column("caso_id", sa.Integer(), nullable=True),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("zapsign_doc_token", sa.String(length=80), nullable=True),
        sa.Column("link_assinatura", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ENVIADO"),
        sa.Column("signatario_nome", sa.String(length=160), nullable=False),
        sa.Column("signatario_email", sa.String(length=160), nullable=True),
        sa.Column("pdf_sha256", sa.String(length=64), nullable=False),
        sa.Column("criado_por", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.Column("assinado_em", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["caso_id"], ["casos.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["criado_por"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("zapsign_doc_token", name="uq_assinaturas_zapsign_doc_token"),
    )
    op.create_index("ix_assinaturas_cliente_id", "assinaturas", ["cliente_id"])
    op.create_index("ix_assinaturas_caso_id", "assinaturas", ["caso_id"])
    op.create_index("ix_assinaturas_status", "assinaturas", ["status"])

    op.create_table(
        "cobrancas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("caso_id", sa.Integer(), nullable=True),
        sa.Column("asaas_payment_id", sa.String(length=40), nullable=False),
        sa.Column("asaas_installment_id", sa.String(length=40), nullable=True),
        sa.Column("forma", sa.String(length=10), nullable=False),
        sa.Column("valor", sa.Numeric(12, 2), nullable=False),
        sa.Column("vencimento", sa.Date(), nullable=False),
        sa.Column("descricao", sa.String(length=200), nullable=True),
        sa.Column("parcela", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("total_parcelas", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDENTE"),
        sa.Column("link_fatura", sa.String(length=500), nullable=True),
        sa.Column("criado_por", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.Column("pago_em", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["caso_id"], ["casos.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["criado_por"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asaas_payment_id", name="uq_cobrancas_asaas_payment_id"),
    )
    op.create_index("ix_cobrancas_cliente_id", "cobrancas", ["cliente_id"])
    op.create_index("ix_cobrancas_caso_id", "cobrancas", ["caso_id"])
    op.create_index("ix_cobrancas_asaas_installment_id", "cobrancas", ["asaas_installment_id"])
    op.create_index("ix_cobrancas_vencimento", "cobrancas", ["vencimento"])
    op.create_index("ix_cobrancas_status", "cobrancas", ["status"])

    op.create_table(
        "eventos_webhook",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("origem", sa.String(length=20), nullable=False),
        sa.Column("evento_id", sa.String(length=160), nullable=False),
        sa.Column("tipo", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("origem", "evento_id", name="uq_evento_webhook"),
    )


def downgrade() -> None:
    # DROP TABLE remove os indices e FKs junto; dropar os indices separadamente
    # falharia no MySQL (1553: index needed in a foreign key constraint).
    op.drop_table("eventos_webhook")
    op.drop_table("cobrancas")
    op.drop_table("assinaturas")
    with op.batch_alter_table("clientes") as batch_op:
        batch_op.drop_constraint("uq_clientes_asaas_customer_id", type_="unique")
        batch_op.drop_column("asaas_customer_id")
