import sqlalchemy as sa
from alembic import op

revision = "0008_lectura_manual"
down_revision = "0007_capacidad_70"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("eventos") as tabla:
        tabla.add_column(
            sa.Column("lectura_manual", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        tabla.add_column(sa.Column("validada_por", sa.String(100), nullable=True))
        tabla.add_column(sa.Column("validada_en", sa.DateTime(timezone=True), nullable=True))
        tabla.add_column(sa.Column("placa_leida", sa.String(20), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("eventos") as tabla:
        tabla.drop_column("placa_leida")
        tabla.drop_column("validada_en")
        tabla.drop_column("validada_por")
        tabla.drop_column("lectura_manual")
