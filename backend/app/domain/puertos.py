from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.domain.cobro import Cobro
    from app.domain.pago import Pago
    from app.domain.tarifa import Tarifa


class RepositorioCobros(Protocol):
    """Guarda y busca cobros. Un solo cobro por placa, sede y día operativo (F-03)."""

    def buscar_del_dia(self, placa: str, sede_id: int, dia: date) -> Cobro | None: ...

    def por_id(self, cobro_id: int) -> Cobro | None: ...

    def guardar(self, cobro: Cobro) -> Cobro: ...


class ConsultaTarifas(Protocol):
    """Solo lectura: la usa el carril (I de SOLID: separada de la administración)."""

    def vigente(self, sede_id: int, tipo: str, franja: str) -> Tarifa: ...


class AdministracionTarifas(Protocol):
    """Escritura: la usa el administrador (HU-09)."""

    def guardar(self, tarifa: Tarifa) -> Tarifa: ...


class PasarelaPago(Protocol):
    """Adapter del medio de pago (HU-05: efectivo). Idempotente: la misma clave no crea
    un segundo pago (F-04). Al pagar, el cobro pasa a PAGADO en la misma operación."""

    def pagar(self, cobro: Cobro, clave_idempotencia: str, fecha_hora: datetime) -> Pago: ...

    def buscar_por_clave(self, clave_idempotencia: str) -> Pago | None: ...