"""Contratos (interfaces) del motor de cobro: HU-04, HU-05 y HU-09.

Siguen el mismo estilo que `ServicioCobroEntrada` en `domain/ingreso.py` (Protocol):
el dominio define QUÉ necesita y la infraestructura (base de datos, pagos) lo implementa.
Principio de inversión de dependencias (D de SOLID): el cálculo del cobro no depende
de SQLAlchemy ni de FastAPI, por eso se puede probar con versiones falsas (fakes).

Para el ingreso (HU-02), el contrato que usa Isaac es `ServicioCobroEntrada`
(en `domain/ingreso.py`); el motor de cobro de la HU-04 lo implementará.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING: 
    from app.domain.cobro import Cobro
    from app.domain.pago import Pago
    from app.domain.tarifa import Tarifa


class RepositorioCobros(Protocol):
    """Guarda y busca cobros. Un solo cobro por placa, sede y día operativo (F-03)."""

    def buscar_del_dia(self, placa: str, sede_id: int, dia: date) -> Cobro | None: ...

    def guardar(self, cobro: Cobro) -> Cobro: ...


class ConsultaTarifas(Protocol):
    """Solo lectura: la usa el carril (I de SOLID: separada de la administración)."""

    def vigente(self, sede_id: int, tipo: str, franja: str) -> Tarifa: ...


class AdministracionTarifas(Protocol):
    """Escritura: la usa el administrador (HU-09)."""

    def guardar(self, tarifa: Tarifa) -> Tarifa: ...


class PasarelaPago(Protocol):
    """Pago idempotente: la misma clave no crea un segundo pago (F-04)."""

    def pagar(self, cobro_id: int, valor: Decimal, clave_idempotencia: str) -> Pago: ...