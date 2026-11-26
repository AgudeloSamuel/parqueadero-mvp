import sqlalchemy as sa
from alembic import op

revision = "0009_parametros"
down_revision = "0008_lectura_manual"
branch_labels = None
depends_on = None


def upgrade() -> None:
    parametros = op.create_table(
        "parametros",
        sa.Column("clave", sa.String(40), primary_key=True),
        sa.Column("valor", sa.String(40), nullable=False),
    )
    # HU-09: hora en que empieza la franja nocturna (configurable por el administrador)
    op.bulk_insert(parametros, [{"clave": "INICIO_NOCTURNA", "valor": "17:30"}])


def downgrade() -> None:
    op.drop_table("parametros")