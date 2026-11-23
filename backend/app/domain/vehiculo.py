"""Clasificación de vehículos por el formato de su placa (HU-03, F-02).

Principio abierto/cerrado (O de SOLID): para agregar un tipo de vehículo nuevo
se registra una regla nueva; la clase Clasificador no se modifica.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

CARRO = "CARRO"
MOTO = "MOTO"


def normalizar_placa(texto: str) -> str:
    """Deja la placa en mayúsculas y sin espacios ni guiones: ' abc-123 ' -> 'ABC123'."""
    return re.sub(r"[\s\-]", "", texto or "").upper()


@dataclass(frozen=True)
class ReglaClasificacion:
    """Asocia un tipo de vehículo con el patrón (expresión regular) de su placa."""

    tipo: str
    patron: str

    def coincide(self, placa: str) -> bool:
        return re.fullmatch(self.patron, placa) is not None


REGLAS_COLOMBIA = (
    ReglaClasificacion(CARRO, r"[A-Z]{3}[0-9]{3}"),      # AAA123
    ReglaClasificacion(MOTO, r"[A-Z]{3}[0-9]{2}[A-Z]"),  # AAA12A
)


class Clasificador:
    """Determina el tipo de vehículo a partir de la placa."""

    def __init__(self, reglas: tuple[ReglaClasificacion, ...] = REGLAS_COLOMBIA) -> None:
        self._reglas = list(reglas)

    def registrar(self, regla: ReglaClasificacion) -> None:
        """Agrega un tipo de vehículo nuevo sin modificar esta clase."""
        self._reglas.append(regla)

    def clasificar(self, placa: str) -> str | None:
        """Devuelve 'CARRO', 'MOTO' (u otro tipo registrado) o None si no se reconoce.

        None significa que la lectura debe pasar a validación manual del operador (F-06).
        """
        placa = normalizar_placa(placa)
        for regla in self._reglas:
            if regla.coincide(placa):
                return regla.tipo
        return None