import sqlalchemy as sa
from alembic import op

revision = "0001_usuarios"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("username", sa.String(100), primary_key=True),
        sa.Column("password_hash", sa.String(60), nullable=False),
        sa.Column("rol", sa.String(8), nullable=False),
        sa.CheckConstraint("rol IN ('OPERADOR', 'ADMIN')", name="ck_usuarios_rol"),
    )


def downgrade() -> None:
    op.drop_table("usuarios")
