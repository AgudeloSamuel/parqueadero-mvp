import sqlalchemy as sa
from alembic import op

revision = "0007_capacidad_70"
down_revision = "0006_cupos"
branch_labels = None
depends_on = None


def _actualizar_capacidad(capacidad: int) -> None:
    cupos = sa.table(
        "cupos", sa.column("tipo_vehiculo", sa.String(12)), sa.column("capacidad", sa.Integer())
    )
    op.execute(
        cupos.update()
        .where(cupos.c.tipo_vehiculo.in_([op.inline_literal("CARRO"), op.inline_literal("MOTO")]))
        .values(capacidad=op.inline_literal(capacidad))
    )


def upgrade() -> None:
    _actualizar_capacidad(70)


def downgrade() -> None:
    _actualizar_capacidad(10)
