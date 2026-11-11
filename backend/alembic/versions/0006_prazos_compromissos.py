"""fase 4 - prazos completos + compromissos de agenda

- prazos: evolucao da TABELA LEGADA (sem estrutura paralela) com
  processo_id opcional, data_inicio, status, prioridade, responsavel_id,
  criado_por, atualizado_em, concluido_em/por e observacoes;
- renomeacoes com BACKFILL REVERSIVEL: `data_limite` -> `data_vencimento`
  e `cumprido` -> `status` (nenhum dado e perdido nos dois sentidos);
- prazo_historicos / compromisso_historicos: auditoria imutavel;
- compromissos: entidade propria de agenda (periodo validado por CHECK);
- indices para as consultas frequentes (filtros da listagem e agenda).

BACKFILL (preserva os dados existentes):
- data_vencimento recebe o valor de data_limite antes de dropar a coluna;
- status = 'CONCLUIDO' quando cumprido, senao 'PENDENTE';
- responsavel_id herda o responsavel do caso (quando existe);
- atualizado_em = criado_em nos registros antigos;
- cada prazo legado ganha um registro CRIACAO com origem MIGRACAO_LEGADA,
  para o historico nao nascer vazio.

No downgrade, `data_limite`/`cumprido` sao recriados e reconstruidos a
partir de `data_vencimento`/`status`. A tabela legada e sempre preservada:
so as colunas novas e as tabelas da Fase 4 sao removidas.

Compatibilidade MySQL: operacoes via batch_alter_table (ALTER TABLE puro no
MySQL, recriacao no SQLite); o CHECK de periodo do compromisso e aplicado
por bancos com suporte a CHECK (SQLite e MySQL 8+); FKs nomeadas
(`fk_prazos_*`, `fk_compromissos_*`) em vez de REFERENCES inline.

Revision ID: 0006_prazos_compromissos
Revises: 0005_processos_judiciais
Create Date: 2026-11-02
"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_prazos_compromissos"
down_revision: Union[str, None] = "0005_processos_judiciais"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) evolucao da tabela legada de prazos ---------------------------
    # data_vencimento e atualizado_em entram nullable: o backfill preenche
    # antes de travar como NOT NULL (ADD COLUMN NOT NULL exige default nao
    # nulo no SQLite, que nao aceita CURRENT_TIMESTAMP como default aqui).
    with op.batch_alter_table("prazos") as batch_op:
        batch_op.add_column(sa.Column("processo_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("data_inicio", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("data_vencimento", sa.Date(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default=sa.text("'PENDENTE'"),
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
        batch_op.add_column(sa.Column("responsavel_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("observacoes", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("criado_por", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("atualizado_em", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("concluido_em", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("concluido_por", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_prazos_processo_id", "processos_judiciais", ["processo_id"], ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_prazos_responsavel_id", "usuarios", ["responsavel_id"], ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_prazos_criado_por", "usuarios", ["criado_por"], ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_prazos_concluido_por", "usuarios", ["concluido_por"], ["id"],
            ondelete="SET NULL",
        )

    # 2) backfill reversivel (dados legados preservados) ---------------
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE prazos SET data_vencimento = data_limite "
            "WHERE data_vencimento IS NULL"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE prazos SET status = CASE WHEN cumprido THEN 'CONCLUIDO' "
            "ELSE 'PENDENTE' END"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE prazos SET responsavel_id = ("
            "SELECT responsavel_id FROM casos WHERE casos.id = prazos.caso_id) "
            "WHERE responsavel_id IS NULL"
        )
    )
    bind.execute(
        sa.text("UPDATE prazos SET atualizado_em = criado_em WHERE atualizado_em IS NULL")
    )

    # 3) remove as colunas legadas (apos o backfill) -------------------
    op.drop_index("ix_prazos_data_limite", table_name="prazos")
    op.drop_index("ix_prazos_cumprido", table_name="prazos")

    with op.batch_alter_table("prazos") as batch_op:
        batch_op.alter_column(
            "data_vencimento", existing_type=sa.Date(), nullable=False
        )
        batch_op.alter_column(
            "atualizado_em", existing_type=sa.DateTime(), nullable=False
        )
        batch_op.drop_column("data_limite")
        batch_op.drop_column("cumprido")

    # 4) indices das consultas frequentes (filtros, ordenacao, escopo) --
    op.create_index("ix_prazos_tipo", "prazos", ["tipo"])
    op.create_index("ix_prazos_data_vencimento", "prazos", ["data_vencimento"])
    op.create_index("ix_prazos_status", "prazos", ["status"])
    op.create_index("ix_prazos_prioridade", "prazos", ["prioridade"])
    op.create_index("ix_prazos_responsavel_id", "prazos", ["responsavel_id"])
    op.create_index("ix_prazos_processo_id", "prazos", ["processo_id"])

    # 5) auditoria de prazos + backfill da migracao --------------------
    op.create_table(
        "prazo_historicos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("prazo_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("operacao", sa.String(length=30), nullable=False),
        sa.Column("dados", sa.JSON(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["prazo_id"], ["prazos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_prazo_historicos_prazo_id", "prazo_historicos", ["prazo_id"]
    )

    # Auditoria do backfill: historico dos prazos legados nasce preenchido.
    # Em modo offline (--sql) nao ha banco para consultar: o backfill de
    # dados roda apenas contra um banco vivo (mesma limitacao da 0005).
    if not op.get_context().as_sql:
        agora = datetime.now()
        prazos = bind.execute(sa.text("SELECT id FROM prazos")).fetchall()
        for (prazo_id,) in prazos:
            bind.execute(
                sa.text(
                    "INSERT INTO prazo_historicos "
                    "(prazo_id, usuario_id, operacao, dados, criado_em) "
                    "VALUES (:pid, NULL, 'CRIACAO', :dados, :em)"
                ),
                {"pid": prazo_id, "dados": '{"origem": "MIGRACAO_LEGADA"}', "em": agora},
            )

    # 6) entidade propria de compromissos (agenda) ---------------------
    op.create_table(
        "compromissos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("caso_id", sa.Integer(), nullable=True),
        sa.Column("processo_id", sa.Integer(), nullable=True),
        sa.Column("titulo", sa.String(length=160), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column(
            "tipo",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'OUTRO'"),
        ),
        sa.Column("data_inicio", sa.DateTime(), nullable=False),
        sa.Column("data_fim", sa.DateTime(), nullable=False),
        sa.Column("local", sa.String(length=200), nullable=True),
        sa.Column("responsavel_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'AGENDADO'"),
        ),
        sa.Column("criado_por", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["caso_id"], ["casos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["processo_id"], ["processos_judiciais.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["responsavel_id"], ["usuarios.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["criado_por"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("data_fim > data_inicio", name="ck_compromissos_periodo"),
    )
    op.create_index("ix_compromissos_caso_id", "compromissos", ["caso_id"])
    op.create_index("ix_compromissos_processo_id", "compromissos", ["processo_id"])
    op.create_index("ix_compromissos_tipo", "compromissos", ["tipo"])
    op.create_index("ix_compromissos_data_inicio", "compromissos", ["data_inicio"])
    op.create_index("ix_compromissos_data_fim", "compromissos", ["data_fim"])
    op.create_index(
        "ix_compromissos_responsavel_id", "compromissos", ["responsavel_id"]
    )
    op.create_index("ix_compromissos_status", "compromissos", ["status"])

    # 7) auditoria de compromissos -------------------------------------
    op.create_table(
        "compromisso_historicos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("compromisso_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("operacao", sa.String(length=30), nullable=False),
        sa.Column("dados", sa.JSON(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["compromisso_id"], ["compromissos.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_compromisso_historicos_compromisso_id",
        "compromisso_historicos",
        ["compromisso_id"],
    )


def downgrade() -> None:
    # A UNICA perda e dos dados criados na Fase 4 (compromissos, suas
    # auditorias, os registros de auditoria de prazos e as colunas novas).
    # Os dados legados de `prazos` sao reconstruidos (data_limite/cumprido),
    # entao nenhum registro antigo e afetado.

    # 0) PRIMEIRO as FKs de prazos: no MySQL um indice usado por uma
    #    constraint nao pode ser removido antes dela (erro 1553) - e
    #    `ix_prazos_processo_id`/`ix_prazos_responsavel_id` podem estar
    #    servindo de indice para as proprias FKs.
    with op.batch_alter_table("prazos") as batch_op:
        batch_op.drop_constraint("fk_prazos_concluido_por", type_="foreignkey")
        batch_op.drop_constraint("fk_prazos_criado_por", type_="foreignkey")
        batch_op.drop_constraint(
            "fk_prazos_responsavel_id", type_="foreignkey"
        )
        batch_op.drop_constraint("fk_prazos_processo_id", type_="foreignkey")

    # 1) remove as tabelas da Fase 4 -----------------------------------
    #    `drop_table` ja remove indices e FKs das proprias tabelas nos dois
    #    bancos (MySQL e SQLite): nao ha drop_index explicito aqui, que e o
    #    que quebrava no MySQL (erro 1553 "needed in a foreign key").
    op.drop_table("compromisso_historicos")
    op.drop_table("compromissos")
    op.drop_table("prazo_historicos")

    # 2) indices novos de prazos ---------------------------------------
    for nome in (
        "ix_prazos_processo_id",
        "ix_prazos_responsavel_id",
        "ix_prazos_prioridade",
        "ix_prazos_status",
        "ix_prazos_data_vencimento",
        "ix_prazos_tipo",
    ):
        op.drop_index(nome, table_name="prazos")

    # 3) recria as colunas legadas a partir das novas ------------------
    with op.batch_alter_table("prazos") as batch_op:
        batch_op.add_column(sa.Column("data_limite", sa.Date(), nullable=True))
        batch_op.add_column(
            sa.Column("cumprido", sa.Boolean(), nullable=False,
                      server_default=sa.text("0"))
        )

    bind = op.get_bind()
    bind.execute(
        sa.text("UPDATE prazos SET data_limite = data_vencimento")
    )
    bind.execute(
        sa.text(
            "UPDATE prazos SET cumprido = CASE WHEN status = 'CONCLUIDO' "
            "THEN 1 ELSE 0 END"
        )
    )

    # 4) remove as colunas novas e restaura o NOT NULL legado -----------
    #    (as FKs ja foram removidas no passo 0)
    with op.batch_alter_table("prazos") as batch_op:
        batch_op.alter_column(
            "data_limite", existing_type=sa.Date(), nullable=False
        )
        batch_op.drop_column("concluido_por")
        batch_op.drop_column("concluido_em")
        batch_op.drop_column("atualizado_em")
        batch_op.drop_column("criado_por")
        batch_op.drop_column("observacoes")
        batch_op.drop_column("responsavel_id")
        batch_op.drop_column("prioridade")
        batch_op.drop_column("status")
        batch_op.drop_column("data_vencimento")
        batch_op.drop_column("data_inicio")
        batch_op.drop_column("processo_id")

    # 5) indices legados -----------------------------------------------
    op.create_index("ix_prazos_cumprido", "prazos", ["cumprido"])
    op.create_index("ix_prazos_data_limite", "prazos", ["data_limite"])
