import pytest

from app.infrastructure.db import motor_db


@pytest.fixture
def configurar_motor():
    motor_db.cache_clear()
    yield motor_db
    motor_db().dispose()
    motor_db.cache_clear()


def test_database_url_tiene_prioridad(configurar_motor, monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg2://postgres:clave%40local@otra-db:5433/otra"
    )
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)

    url = configurar_motor().url

    assert url.drivername == "postgresql+psycopg2"
    assert (url.host, url.port, url.database) == ("otra-db", 5433, "otra")
    assert url.password == "clave@local"


def test_sin_database_url_usa_configuracion_de_compose(configurar_motor, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_USER", "parqueadero")
    monkeypatch.setenv("POSTGRES_DB", "parqueadero")
    monkeypatch.setenv("POSTGRES_PASSWORD", "clave@local")

    url = configurar_motor().url

    assert url.drivername == "postgresql+psycopg2"
    assert (url.host, url.username, url.database) == ("db", "parqueadero", "parqueadero")
    assert url.password == "clave@local"
