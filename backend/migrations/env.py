from alembic import context

from app.infrastructure.db import Base, motor_db

if context.is_offline_mode():
    context.configure(dialect_name="postgresql", target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
else:
    with motor_db().connect() as conexion:
        context.configure(connection=conexion, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
