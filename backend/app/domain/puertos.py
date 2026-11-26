from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.domain.cobro import Cobro
    from app.domain.pago import Pago
    from app.domain.tarifa import Tarifa


class RepositorioCobros(Protocol):
    

    def buscar_del_dia(self, placa: str, sede_id: int, dia: date) -> Cobro | None: ...

    def por_id(self, cobro_id: int) -> Cobro | None: ...

    def guardar(self, cobro: Cobro) -> Cobro: ...


class ConsultaTarifas(Protocol):
   

    def vigente(self, sede_id: int, tipo: str, franja: str) -> Tarifa: ...


class HorarioFranjas(Protocol):
  

    def inicio_nocturna(self) -> time: ...


class AdministracionTarifas(Protocol):
   

    def listar(self) -> list[Tarifa]: ...

    def actualizar(self, tipo: str, diurna: int, nocturna: int) -> list[Tarifa]: ...

    def cambiar_inicio_nocturna(self, inicio: time) -> None: ...


class PasarelaPago(Protocol):

    def pagar(self, cobro: Cobro, clave_idempotencia: str, fecha_hora: datetime) -> Pago: ...

    def buscar_por_clave(self, clave_idempotencia: str) -> Pago | None: ...