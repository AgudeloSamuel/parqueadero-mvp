import sqlalchemy as sa
from alembic import op

revision = "0004_pagos"
down_revision = "0003_tarifas_cobros"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pagos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cobro_id", sa.Integer(), sa.ForeignKey("cobros.id"), nullable=False),
        sa.Column("valor", sa.Integer(), nullable=False),
        sa.Column("clave_idempotencia", sa.String(100), nullable=False),
        sa.Column("fecha_hora", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("valor >= 0", name="ck_pagos_valor"),
        # Un cobro se paga una sola vez y una clave no se repite (F-04)
        sa.UniqueConstraint("cobro_id", name="uq_pagos_cobro"),
        sa.UniqueConstraint("clave_idempotencia", name="uq_pagos_clave"),
    )


def downgrade() -> None:
    op.drop_table("pagos") 