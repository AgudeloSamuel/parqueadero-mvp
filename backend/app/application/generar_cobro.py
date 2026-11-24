from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from app.domain.cobro import Cobro
from app.domain.ingreso import CobroEntrada
from app.domain.puertos import RepositorioCobros
from app.domain.tarifa import EstrategiaTarifa


class TipoSinTarifa(LookupError):
    pass


class ServicioCobro:
    def __init__(
        self,
        repositorio: RepositorioCobros,
        estrategias: Mapping[str, EstrategiaTarifa],
    ) -> None:
        self.repositorio = repositorio
        self.estrategias = estrategias

    def generar_o_reutilizar(
        self, placa: str, tipo: str, sede_id: int, fecha_hora: datetime
    ) -> CobroEntrada | None:
        dia = fecha_hora.date()  # S-02: día operativo = fecha de la entrada
        existente = self.repositorio.buscar_del_dia(placa, sede_id, dia)
        if existente is not None:  # reingreso el mismo día: cobro único
            return self._para_entrada(existente)

        estrategia = self.estrategias.get(tipo)
        if estrategia is None:
            raise TipoSinTarifa(f"No hay tarifa configurada para {tipo}")
        tarifa = estrategia.calcular(tipo, sede_id, fecha_hora)
        if tarifa.valor == 0:  # RN-01: moto $0 -> no se genera cobro
            return None

        cobro = Cobro(
            placa=placa,
            sede_id=sede_id,
            dia_operativo=dia,
            tipo_vehiculo=tipo,
            tarifa_id=tarifa.id,
            valor=tarifa.valor,  # RN-07: el valor queda guardado en el cobro
            estado="PENDIENTE",
            creado_en=fecha_hora,
        )
        return self._para_entrada(self.repositorio.guardar(cobro))

    @staticmethod
    def _para_entrada(cobro: Cobro) -> CobroEntrada:
        return CobroEntrada(id=cobro.id, valor=cobro.valor, estado=cobro.estado)