"""Caso de uso de la HU-05: pagar en efectivo el cobro del día."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from app.domain.pago import ClaveDeOtroCobro, Pago, pase_hasta
from app.domain.puertos import PasarelaPago, RepositorioCobros


class CobroNoEncontrado(LookupError):
    pass


@dataclass(frozen=True)
class ResultadoPago:
    pago: Pago
    estado_cobro: str
    pase_hasta: datetime


class PagarCobro:
    def __init__(
        self,
        cobros: RepositorioCobros,
        pasarela: PasarelaPago,
        ahora: Callable[[], datetime],
    ) -> None:
        self.cobros = cobros
        self.pasarela = pasarela
        self.ahora = ahora

    def ejecutar(self, cobro_id: int, clave_idempotencia: str) -> ResultadoPago:
        momento = self.ahora()
        cobro = self.cobros.por_id(cobro_id)
        if cobro is None:
            raise CobroNoEncontrado("Cobro no encontrado")

        previo = self.pasarela.buscar_por_clave(clave_idempotencia)
        if previo is not None:  # F-04: la misma solicitud repetida devuelve el mismo pago
            if previo.cobro_id != cobro_id:
                raise ClaveDeOtroCobro("La clave de idempotencia ya se usó para otro cobro")
            pago = previo
        else:
            cobro.ciclo.pagar()  # State: lanza error si el cobro ya está PAGADO o ANULADO
            pago = self.pasarela.pagar(cobro, clave_idempotencia, momento)

        return ResultadoPago(
            pago=pago,
            estado_cobro="PAGADO",
            pase_hasta=pase_hasta(cobro.dia_operativo, momento.tzinfo),  # RN-03
        )