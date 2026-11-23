"""andamentos: origem (manual/DataJud) e chave externa para nao duplicar a sincronizacao"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009_andamentos_origem"
down_revision: Union[str, None] = "0008_notificacoes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("andamentos") as lote:
        lote.add_column(sa.Column("origem", sa.String(length=20), nullable=False, server_default="MANUAL"))
        lote.add_column(sa.Column("chave_externa", sa.String(length=64), nullable=True))
        lote.create_unique_constraint("uq_andamento_caso_chave", ["caso_id", "chave_externa"])


def downgrade() -> None:
    with op.batch_alter_table("andamentos") as lote:
        lote.drop_constraint("uq_andamento_caso_chave", type_="unique")
        lote.drop_column("chave_externa")
        lote.drop_column("origem")
