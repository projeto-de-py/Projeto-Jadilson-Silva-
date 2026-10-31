"""fase 1 - clientes, controle de acesso por caso e evolucao do usuario

- clientes: cadastro cadastral (PF/PJ) com UNIQUE em cpf_cnpj (NULL ignorado);
- usuario_casos: M:N usuario<->caso com permissoes, UNIQUE(usuario_id, caso_id)
  e historico de concessao/revogacao (rastreabilidade);
- usuarios: +administrador (advogado principal), +atualizado_em e perfis
  funcionais ADVOGADO/FUNCIONARIO (dados existentes sao convertidos, nunca
  apagados: ADMIN -> ADVOGADO com administrador=1; PADRAO -> ADVOGADO);
- casos: +cliente_id (FK anulavel) vinculando o caso ao cadastro de clientes.

Revision ID: 0003_fase1_cadastros
Revises: 0002_casos_prazos
Create Date: 2026-10-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_fase1_cadastros"
down_revision: Union[str, None] = "0002_casos_prazos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) clientes ----------------------------------------------------------
    op.create_table(
        "clientes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nome", sa.String(length=160), nullable=False),
        sa.Column("cpf_cnpj", sa.String(length=14), nullable=True),
        sa.Column("email", sa.String(length=160), nullable=True),
        sa.Column("telefone", sa.String(length=20), nullable=True),
        sa.Column("data_nascimento", sa.Date(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cpf_cnpj", name="uq_clientes_cpf_cnpj"),
    )
    op.create_index("ix_clientes_nome", "clientes", ["nome"])

    # 2) usuario_casos -----------------------------------------------------
    op.create_table(
        "usuario_casos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("caso_id", sa.Integer(), nullable=False),
        sa.Column("pode_visualizar", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("pode_registrar_andamento", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("pode_gerenciar_prazos", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("concedido_por", sa.Integer(), nullable=True),
        sa.Column("concedido_em", sa.DateTime(), nullable=False),
        sa.Column("revogado_por", sa.Integer(), nullable=True),
        sa.Column("revogado_em", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["caso_id"], ["casos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["concedido_por"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["revogado_por"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("usuario_id", "caso_id", name="uq_usuario_caso"),
    )
    op.create_index("ix_usuario_casos_usuario_id", "usuario_casos", ["usuario_id"])
    op.create_index("ix_usuario_casos_caso_id", "usuario_casos", ["caso_id"])

    # 3) usuarios: administrador + atualizado_em + novos perfis -------------
    # batch_alter_table: gera ALTER TABLE no MySQL e recria a tabela no SQLite
    # (unicos dialectos com limitacoes diferentes para ADD COLUMN NOT NULL).
    with op.batch_alter_table("usuarios") as batch_op:
        batch_op.add_column(
            sa.Column(
                "administrador",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "atualizado_em",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )
        batch_op.alter_column(
            "perfil",
            existing_type=sa.String(length=10),
            type_=sa.String(length=20),
            existing_nullable=False,
            server_default=sa.text("'ADVOGADO'"),
        )

    # Dados existentes preservados e convertidos (nenhuma linha apagada).
    op.execute(
        "UPDATE usuarios SET administrador = 1, perfil = 'ADVOGADO' "
        "WHERE perfil = 'ADMIN'"
    )
    op.execute("UPDATE usuarios SET perfil = 'ADVOGADO' WHERE perfil = 'PADRAO'")

    # 4) casos.cliente_id --------------------------------------------------
    with op.batch_alter_table("casos") as batch_op:
        batch_op.add_column(sa.Column("cliente_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_casos_cliente_id", ["cliente_id"])
        batch_op.create_foreign_key(
            "fk_casos_cliente_id", "clientes", ["cliente_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    # remove primeiro as linhas que apontam para usuarios/casos
    op.drop_table("usuario_casos")

    with op.batch_alter_table("casos") as batch_op:
        batch_op.drop_constraint("fk_casos_cliente_id", type_="foreignkey")
        batch_op.drop_index("ix_casos_cliente_id")
        batch_op.drop_column("cliente_id")

    # reverte o mapeamento de perfis antes de encolher a coluna
    # (nao ha como distinguir quem era ADVOGADO colaborador de quem era
    # FUNCIONARIO: ambos voltam para PADRAO, comportamento pre-Fase 1)
    op.execute("UPDATE usuarios SET perfil = 'ADMIN' WHERE administrador = 1")
    op.execute(
        "UPDATE usuarios SET perfil = 'PADRAO' "
        "WHERE perfil IN ('ADVOGADO', 'FUNCIONARIO')"
    )

    with op.batch_alter_table("usuarios") as batch_op:
        batch_op.alter_column(
            "perfil",
            existing_type=sa.String(length=20),
            type_=sa.String(length=10),
            existing_nullable=False,
            server_default=sa.text("'PADRAO'"),
        )
        batch_op.drop_column("atualizado_em")
        batch_op.drop_column("administrador")

    op.drop_table("clientes")
