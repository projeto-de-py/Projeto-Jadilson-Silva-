"""fase 3 - processos judiciais vinculados aos casos

- processos_judiciais: entidade propria (N:1 Caso) com numero CNJ normalizado
  (20 digitos) e unico, tribunal/orgao julgador/comarca/instancia/classe/
  assunto/data de distribuicao/status/valor da causa/segredo de justica,
  arquivamento logico proprio e rastreio do criador;
- processo_historicos: auditoria imutavel das operacoes de processo;
- usuario_casos: +pode_gerenciar_processos (concessao para criar/editar
  processos; default False preserva o menor privilegio dos registros legados).

BACKFILL (compatibilidade com o campo legado `casos.numero_processo`):
os numeros de processo dos casos existentes sao migrados para
`processos_judiciais` SOMENTE quando validos pelo padrao CNJ (20 digitos com
digitos verificadores, modulo 97). Numeros legados invalidos permanecem apenas
em `casos.numero_processo` (que NAO e removido nesta fase). A coluna legada e
mantida por integridade com dados antigos e com o frontend existente.

Revision ID: 0005_processos_judiciais
Revises: 0004_casos_gestao
Create Date: 2026-11-01
"""
import re
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_processos_judiciais"
down_revision: Union[str, None] = "0004_casos_gestao"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NAO_DIGITOS = re.compile(r"\D")


def _apenas_digitos(valor: str) -> str:
    return _NAO_DIGITOS.sub("", valor or "")


def _eh_cnj(numero: str) -> bool:
    """Valida o numero CNJ: 20 digitos com resto 1 na divisao por 97."""
    if len(numero) != 20 or not numero.isdigit() or len(set(numero)) == 1:
        return False
    return int(numero) % 97 == 1


def upgrade() -> None:
    # 1) entidade de processos -------------------------------------------
    op.create_table(
        "processos_judiciais",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("caso_id", sa.Integer(), nullable=False),
        sa.Column("numero_processo", sa.String(length=20), nullable=False),
        sa.Column("tribunal", sa.String(length=120), nullable=True),
        sa.Column("orgao_julgador", sa.String(length=160), nullable=True),
        sa.Column("comarca", sa.String(length=120), nullable=True),
        sa.Column("instancia", sa.String(length=20), nullable=True),
        sa.Column("classe_processual", sa.String(length=80), nullable=True),
        sa.Column("assunto", sa.String(length=200), nullable=True),
        sa.Column("data_distribuicao", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("valor_causa", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("segredo_justica", sa.Boolean(), nullable=False),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("arquivado", sa.Boolean(), nullable=False),
        sa.Column("arquivado_por", sa.Integer(), nullable=True),
        sa.Column("arquivado_em", sa.DateTime(), nullable=True),
        sa.Column("criado_por", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["caso_id"], ["casos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["criado_por"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["arquivado_por"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("numero_processo", name="uq_processos_numero"),
        sa.CheckConstraint("valor_causa >= 0", name="ck_processos_valor_causa"),
    )
    # indices para os filtros da listagem
    op.create_index("ix_processos_caso_id", "processos_judiciais", ["caso_id"])
    op.create_index("ix_processos_tribunal", "processos_judiciais", ["tribunal"])
    op.create_index("ix_processos_comarca", "processos_judiciais", ["comarca"])
    op.create_index("ix_processos_instancia", "processos_judiciais", ["instancia"])
    op.create_index(
        "ix_processos_classe_processual", "processos_judiciais", ["classe_processual"]
    )
    op.create_index("ix_processos_status", "processos_judiciais", ["status"])
    op.create_index(
        "ix_processos_data_distribuicao", "processos_judiciais", ["data_distribuicao"]
    )
    op.create_index("ix_processos_arquivado", "processos_judiciais", ["arquivado"])

    # 2) auditoria de processos ------------------------------------------
    op.create_table(
        "processo_historicos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("processo_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("operacao", sa.String(length=20), nullable=False),
        sa.Column("dados", sa.JSON(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["processo_id"], ["processos_judiciais.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_processo_historicos_processo_id", "processo_historicos", ["processo_id"]
    )

    # 3) nova permissao granular (default False = menor privilegio) ------
    op.add_column(
        "usuario_casos",
        sa.Column(
            "pode_gerenciar_processos",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    # 4) backfill: numeros legados validos viram processos ---------------
    # Feito em Python porque a validacao dos digitos verificadores exige
    # modulo 97 (nao portavel em SQL entre SQLite e MySQL). Somente numeros
    # CNJ-validos sao migrados; invalidos permanecem so no caso legado.
    bind = op.get_bind()
    casos = bind.execute(
        sa.text(
            "SELECT id, numero_processo, tribunal, vara, status, arquivado, "
            "arquivado_por, arquivado_em, criado_por, criado_em FROM casos "
            "WHERE numero_processo IS NOT NULL"
        )
    ).fetchall()

    agora = datetime.now()
    for caso in casos:
        digitos = _apenas_digitos(caso[1])
        if not _eh_cnj(digitos):
            continue  # numero legado invalido: preservado apenas no caso
        # colunas do SELECT: id, numero, tribunal, vara, status, arquivado,
        # arquivado_por, arquivado_em, criado_por, criado_em
        bind.execute(
            sa.text(
                "INSERT INTO processos_judiciais "
                "(caso_id, numero_processo, tribunal, orgao_julgador, status, "
                " segredo_justica, arquivado, arquivado_por, arquivado_em, "
                " criado_por, criado_em, atualizado_em) "
                "VALUES (:caso_id, :numero, :tribunal, :orgao, :status, "
                " :segredo, :arquivado, :arquivado_por, :arquivado_em, "
                " :criado_por, :criado_em, :atualizado_em)"
            ),
            {
                "caso_id": caso[0],
                "numero": digitos,
                "tribunal": caso[2],
                "orgao": caso[3],  # vara legada vira o orgao julgador
                "status": "EM_ANDAMENTO",
                "segredo": False,
                "arquivado": bool(caso[5]),
                "arquivado_por": caso[6],
                "arquivado_em": caso[7],
                "criado_por": caso[8],
                "criado_em": caso[9] or agora,
                "atualizado_em": agora,
            },
        )

    # Auditoria do backfill: cada processo migrado ganha um registro CRIACAO
    # sem usuario (operador de sistema), para o historico nao nascer vazio.
    migrados_ids = bind.execute(
        sa.text("SELECT id FROM processos_judiciais")
    ).fetchall()
    for (proc_id,) in migrados_ids:
        existe = bind.execute(
            sa.text(
                "SELECT 1 FROM processo_historicos "
                "WHERE processo_id = :pid AND operacao = 'CRIACAO'"
            ),
            {"pid": proc_id},
        ).first()
        if not existe:
            bind.execute(
                sa.text(
                    "INSERT INTO processo_historicos "
                    "(processo_id, usuario_id, operacao, dados, criado_em) "
                    "VALUES (:pid, NULL, 'CRIACAO', :dados, :em)"
                ),
                {
                    "pid": proc_id,
                    "dados": '{"origem": "MIGRACAO_LEGADA"}',
                    "em": agora,
                },
            )


def downgrade() -> None:
    # Reverte para o estado pre-Fase 3. A UNICA perda e dos dados criados na
    # Fase 3 (processos + sua auditoria + a coluna de permissao) - e a unica
    # perda possivel num downgrade. `casos.numero_processo` (legado) permanece
    # intacto, entao nenhum registro antigo e afetado.
    # As tabelas da Fase 3 sao removidas por `drop_table`, que tambem remove
    # indices e FKs das proprias tabelas nos dois bancos (MySQL e SQLite).
    # Nao ha drop_index explicito aqui: no MySQL ele falharia com o erro 1553
    # ("needed in a foreign key constraint") quando o indice e o que sustenta
    # uma FK da propria tabela (ex.: ix_processo_historicos_processo_id).
    op.drop_table("processo_historicos")
    op.drop_table("processos_judiciais")

    op.drop_column("usuario_casos", "pode_gerenciar_processos")
