"""Pruebas de la HU-03: clasificar el vehículo por su placa."""
import pytest

from app.domain.vehiculo import (
    CARRO,
    MOTO,
    Clasificador,
    ReglaClasificacion,
    normalizar_placa,
)


@pytest.fixture
def clasificador():
    return Clasificador()


# Criterio 1: AAA123 se clasifica como CARRO
@pytest.mark.parametrize("placa", ["ABC123", "XYZ987", "MNO000"])
def test_placa_de_carro(clasificador, placa):
    assert clasificador.clasificar(placa) == CARRO


# Criterio 2: AAA12A se clasifica como MOTO
@pytest.mark.parametrize("placa", ["ABC12D", "XYZ98Z", "QWE01A"])
def test_placa_de_moto(clasificador, placa):
    assert clasificador.clasificar(placa) == MOTO


# Criterio 3 (prueba de error): otro formato no se reconoce -> validación manual
@pytest.mark.parametrize("placa", ["1234AB", "AB123", "ABCD123", "ABC1234", "", "ABC12", "A1B2C3"])
def test_formato_no_reconocido(clasificador, placa):
    assert clasificador.clasificar(placa) is None


# La placa leída se normaliza: minúsculas, espacios y guiones
@pytest.mark.parametrize("entrada, esperado", [
    ("abc123", "ABC123"),
    (" ABC 123 ", "ABC123"),
    ("abc-12d", "ABC12D"),
    (None, ""),
])
def test_normalizar_placa(entrada, esperado):
    assert normalizar_placa(entrada) == esperado


def test_clasifica_placa_sin_normalizar(clasificador):
    assert clasificador.clasificar("abc-123") == CARRO
    assert clasificador.clasificar(" xyz 98z ") == MOTO


# Criterio 4: agregar un tipo nuevo solo requiere registrar un patrón (abierto/cerrado)
def test_registrar_tipo_nuevo_sin_modificar_clasificador(clasificador):
    assert clasificador.clasificar("AB1234") is None
    clasificador.registrar(ReglaClasificacion("CAMIONETA", r"[A-Z]{2}[0-9]{4}"))
    assert clasificador.clasificar("AB1234") == "CAMIONETA"
    # los tipos existentes siguen funcionando igual
    assert clasificador.clasificar("ABC123") == CARRO
    assert clasificador.clasificar("ABC12D") == MOTO