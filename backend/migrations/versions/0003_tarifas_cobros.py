import sqlalchemy as sa
from alembic import op

revision = "0003_tarifas_cobros"
down_revision = "0002_eventos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tarifas = op.create_table(
        "tarifas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tipo_vehiculo", sa.String(12), nullable=False),
        sa.Column("franja", sa.String(10), nullable=False),
        sa.Column("valor", sa.Integer(), nullable=False),
        sa.CheckConstraint("valor >= 0", name="ck_tarifas_valor"),
        sa.CheckConstraint("franja IN ('DIURNA', 'NOCTURNA')", name="ck_tarifas_franja"),
        sa.UniqueConstraint("tipo_vehiculo", "franja", name="uq_tarifas_tipo_franja"),
    )

    op.bulk_insert(
        tarifas,
        [
            {"tipo_vehiculo": "CARRO", "franja": "DIURNA", "valor": 3850},
            {"tipo_vehiculo": "CARRO", "franja": "NOCTURNA", "valor": 1800},
            {"tipo_vehiculo": "MOTO", "franja": "DIURNA", "valor": 0},
            {"tipo_vehiculo": "MOTO", "franja": "NOCTURNA", "valor": 0},
        ],
    )
    op.create_table(
        "cobros",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("placa", sa.String(20), nullable=False),
        sa.Column("sede_id", sa.Integer(), nullable=False),
        sa.Column("dia_operativo", sa.Date(), nullable=False),
        sa.Column("tipo_vehiculo", sa.String(12), nullable=False),
        sa.Column("tarifa_id", sa.Integer(), sa.ForeignKey("tarifas.id"), nullable=False),
        sa.Column("valor", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(12), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("valor >= 0", name="ck_cobros_valor"),
        sa.UniqueConstraint("placa", "sede_id", "dia_operativo", name="uq_cobro_placa_sede_dia"),
    )


def downgrade() -> None:
    op.drop_table("cobros")
    op.drop_table("tarifas")