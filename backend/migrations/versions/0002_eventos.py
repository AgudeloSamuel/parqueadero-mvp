import sqlalchemy as sa
from alembic import op

revision = "0002_eventos"
down_revision = "0001_usuarios"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eventos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tipo", sa.String(16), nullable=False),
        sa.Column("placa", sa.String(20), nullable=False),
        sa.Column("confianza", sa.Float(), nullable=False),
        sa.Column("sede_id", sa.Integer(), nullable=False),
        sa.Column("fecha_hora", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tipo_vehiculo", sa.String(12), nullable=False),
        sa.Column("barrera", sa.String(24), nullable=False),
        sa.Column("motivo", sa.String(160), nullable=False),
        sa.CheckConstraint("confianza BETWEEN 0 AND 1", name="ck_eventos_confianza"),
    )


def downgrade() -> None:
    op.drop_table("eventos")
