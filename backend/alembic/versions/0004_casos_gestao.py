"""fase 2 - gerenciamento de casos juridicos + auditoria

- casos: +titulo, +tipo_demanda, +prioridade, +data_abertura (backfill a partir
  de criado_em), +responsavel_id (FK), +observacoes, +arquivado/por/em (soft
  delete), +criado_por (FK), +atualizado_em; numero_processo deixa de ser
  obrigatorio (um caso pode ser administrativo/extrajudicial - o UNIQUE
  permanece e ignora NULL, entao casos sem processo nao colidem);
- caso_historicos: auditoria imutavel das alteracoes (caso, usuario, operacao,
  dados JSON com antes/depois).

Nenhuma tabela e apagada e nenhum registro e excluido; os dados legados sao
preservados e enriquecidos (titulo = numero_processo quando existir).

Revision ID: 0004_casos_gestao
Revises: 0003_fase1_cadastros
Create Date: 2026-10-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_casos_gestao"
down_revision: Union[str, None] = "0003_fase1_cadastros"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) auditoria --------------------------------------------------------
    op.create_table(
        "caso_historicos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("caso_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("operacao", sa.String(length=20), nullable=False),
        sa.Column("dados", sa.JSON(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["caso_id"], ["casos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_caso_historicos_caso_id", "caso_historicos", ["caso_id"])

    # 2) novas colunas de casos ------------------------------------------
    # batch_alter_table: gera ALTER TABLE no MySQL e recria a tabela no SQLite
    # (unicos dialectos com limitacoes diferentes para estas operacoes).
    with op.batch_alter_table("casos") as batch_op:
        batch_op.add_column(sa.Column("titulo", sa.String(length=200), nullable=True))
        batch_op.add_column(
            sa.Column(
                "tipo_demanda",
                sa.String(length=20),
                nullable=False,
                server_default=sa.text("'JUDICIAL'"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "prioridade",
                sa.String(length=10),
                nullable=False,
                server_default=sa.text("'MEDIA'"),
            )
        )
        batch_op.add_column(sa.Column("data_abertura", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("responsavel_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("observacoes", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "arquivado",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch_op.add_column(sa.Column("arquivado_por", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("arquivado_em", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("criado_por", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "atualizado_em",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )
        # numero_processo opcional: casos administrativos/extrajudiciais nao
        # tem numero de processo judicial (o UNIQUE permanece, ignora NULL).
        batch_op.alter_column(
            "numero_processo",
            existing_type=sa.String(length=30),
            nullable=True,
        )
        batch_op.create_foreign_key(
            "fk_casos_responsavel_id", "usuarios", ["responsavel_id"], ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_casos_arquivado_por", "usuarios", ["arquivado_por"], ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_casos_criado_por", "usuarios", ["criado_por"], ["id"],
            ondelete="SET NULL",
        )

    # 3) indices para os filtros/ordenacoes da listagem -------------------
    op.create_index("ix_casos_titulo", "casos", ["titulo"])
    op.create_index("ix_casos_tipo_demanda", "casos", ["tipo_demanda"])
    op.create_index("ix_casos_data_abertura", "casos", ["data_abertura"])
    op.create_index("ix_casos_responsavel_id", "casos", ["responsavel_id"])
    op.create_index("ix_casos_arquivado", "casos", ["arquivado"])
    # `area` ganhou filtro na Fase 2 e ainda nao tinha indice.
    op.create_index("ix_casos_area", "casos", ["area"])

    # 4) dados legados preservados e enriquecidos -------------------------
    # titulo: os casos antigos se identificavam pelo numero do processo.
    op.execute("UPDATE casos SET titulo = numero_processo WHERE titulo IS NULL")
    # data_abertura: melhor aproximacao disponivel e a criacao do registro.
    op.execute("UPDATE casos SET data_abertura = DATE(criado_em) WHERE data_abertura IS NULL")


def downgrade() -> None:
    # Reverte para o estado pre-Fase 2. ATENCAO: os campos novos (titulo,
    # tipo_demanda, prioridade, data_abertura, responsavel, observacoes,
    # arquivamento, auditoria) sao descartados - e a unica perda possivel num
    # downgrade; nenhum registro legado e afetado (numero_processo NOT NULL e
    # restaurado apenas para quem ja tinha numero).

    # 0) PRIMEIRO as FKs: no MySQL um indice usado por uma constraint nao
    #    pode ser removido antes dela (erro 1553) - `ix_casos_responsavel_id`
    #    e o indice que sustenta `fk_casos_responsavel_id`.
    with op.batch_alter_table("casos") as batch_op:
        batch_op.drop_constraint("fk_casos_criado_por", type_="foreignkey")
        batch_op.drop_constraint("fk_casos_arquivado_por", type_="foreignkey")
        batch_op.drop_constraint("fk_casos_responsavel_id", type_="foreignkey")

    op.drop_index("ix_casos_area", table_name="casos")
    op.drop_index("ix_casos_arquivado", table_name="casos")
    op.drop_index("ix_casos_responsavel_id", table_name="casos")
    op.drop_index("ix_casos_data_abertura", table_name="casos")
    op.drop_index("ix_casos_tipo_demanda", table_name="casos")
    op.drop_index("ix_casos_titulo", table_name="casos")

    op.drop_table("caso_historicos")

    with op.batch_alter_table("casos") as batch_op:
        batch_op.drop_column("atualizado_em")
        batch_op.drop_column("criado_por")
        batch_op.drop_column("arquivado_em")
        batch_op.drop_column("arquivado_por")
        batch_op.drop_column("arquivado")
        batch_op.drop_column("observacoes")
        batch_op.drop_column("responsavel_id")
        batch_op.drop_column("data_abertura")
        batch_op.drop_column("prioridade")
        batch_op.drop_column("tipo_demanda")
        batch_op.drop_column("titulo")

    # Restaura a obrigatoriedade de numero_processo. Casos criados na Fase 2
    # SEM numero (administrativos/extrajudiciais) viram "S/N-<id>": um marcador
    # reversivel e visivel, evitando perder a linha ou violar o NOT NULL.
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        op.execute(
            "UPDATE casos SET numero_processo = CONCAT('S/N-', id) "
            "WHERE numero_processo IS NULL"
        )
    else:  # sqlite
        op.execute(
            "UPDATE casos SET numero_processo = 'S/N-' || id "
            "WHERE numero_processo IS NULL"
        )

    with op.batch_alter_table("casos") as batch_op:
        batch_op.alter_column(
            "numero_processo",
            existing_type=sa.String(length=30),
            nullable=False,
        )
