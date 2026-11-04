"""fase 4 - permissao propria para compromissos de agenda

- usuario_casos: +pode_gerenciar_compromissos (Boolean NOT NULL default 0).

Compromisso e recurso DISTINTO de prazo: quem tem apenas
`pode_gerenciar_prazos` NAO passa a gerenciar a agenda por implicito.

NAO ha backfill: as linhas existentes nascem com False (menor privilegio) -
ninguem recebe a nova permissao automaticamente; o administrador concede
pela rota `POST /api/casos/{id}/usuarios`.

Compatibilidade MySQL: `ADD COLUMN ... NOT NULL DEFAULT 0` e suportado pelo
MySQL 8 (INNODB) e pelo SQLite (ALTER TABLE ADD COLUMN com default nao-nulo).

Revision ID: 0007_permissoes_compromissos
Revises: 0006_prazos_compromissos
Create Date: 2026-11-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_permissoes_compromissos"
down_revision: Union[str, None] = "0006_prazos_compromissos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default 0 = as linhas legadas ficam SEM a permissao (sem backfill
    # de privilegio: o admin concede caso a caso pela API).
    op.add_column(
        "usuario_casos",
        sa.Column(
            "pode_gerenciar_compromissos",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    # Remove somente a coluna nova; nenhuma outra tabela/dado e afetado.
    op.drop_column("usuario_casos", "pode_gerenciar_compromissos")
