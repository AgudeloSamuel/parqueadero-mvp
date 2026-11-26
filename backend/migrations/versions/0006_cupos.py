import sqlalchemy as sa
from alembic import op

revision = "0006_cupos"
down_revision = "0005_lectura_sin_placa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cupos = op.create_table(
        "cupos",
        sa.Column("tipo_vehiculo", sa.String(12), primary_key=True),
        sa.Column("capacidad", sa.Integer(), nullable=False),
        sa.CheckConstraint("capacidad >= 0", name="ck_cupos_capacidad"),
    )
    op.bulk_insert(cupos, [
        {"tipo_vehiculo": "CARRO", "capacidad": 10},
        {"tipo_vehiculo": "MOTO", "capacidad": 10},
    ])
    op.create_index(
        "ix_eventos_ocupacion", "eventos", ["sede_id", "tipo_vehiculo", "placa", "id"]
    )


def downgrade() -> None:
    op.drop_index("ix_eventos_ocupacion", table_name="eventos")
    op.drop_table("cupos")
