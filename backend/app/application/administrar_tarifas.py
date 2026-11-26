from __future__ import annotations

from datetime import time

from app.domain.puertos import AdministracionTarifas, HorarioFranjas
from app.domain.tarifa import Tarifa, validar_inicio_nocturna, validar_tarifas


class TipoSinTarifas(LookupError):
    pass


class AdministrarTarifas:
    def __init__(self, tarifas: AdministracionTarifas, horario: HorarioFranjas) -> None:
        self.tarifas = tarifas
        self.horario = horario

    def listar(self) -> list[Tarifa]:
        return self.tarifas.listar()

    def cambiar_tarifas(self, tipo: str, diurna: int, nocturna: int) -> list[Tarifa]:
        validar_tarifas(diurna, nocturna)  # RN-02: se valida ANTES de guardar
        tipo = tipo.upper()
        if not any(t.tipo_vehiculo == tipo for t in self.tarifas.listar()):
            raise TipoSinTarifas(f"No hay tarifas para el tipo de vehículo {tipo}")
        return self.tarifas.actualizar(tipo, diurna, nocturna)

    def inicio_nocturna(self) -> time:
        return self.horario.inicio_nocturna()

    def cambiar_inicio_nocturna(self, inicio: time) -> time:
        validar_inicio_nocturna(inicio)
        self.tarifas.cambiar_inicio_nocturna(inicio)
        return inicio