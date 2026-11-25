import sqlalchemy as sa
from alembic import op

revision = "0005_lectura_sin_placa"
down_revision = "0004_pagos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("eventos") as tabla:
        tabla.alter_column("placa", existing_type=sa.String(20), nullable=True)
        tabla.alter_column("tipo_vehiculo", existing_type=sa.String(12), nullable=True)


def downgrade() -> None:
    eventos = sa.table(
        "eventos", sa.column("placa", sa.String(20)), sa.column("tipo_vehiculo", sa.String(12))
    )
    pendientes = sa.select(sa.func.count()).select_from(eventos).where(
        sa.or_(eventos.c.placa.is_(None), eventos.c.tipo_vehiculo.is_(None))
    )
    if op.get_bind().scalar(pendientes):
        raise RuntimeError("Resuelve las lecturas sin placa antes de revertir esta migración")
    with op.batch_alter_table("eventos") as tabla:
        tabla.alter_column("placa", existing_type=sa.String(20), nullable=False)
        tabla.alter_column("tipo_vehiculo", existing_type=sa.String(12), nullable=False)
