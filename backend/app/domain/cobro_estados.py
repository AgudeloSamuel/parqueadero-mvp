"""Patrón State del cobro (HU-05)."""
from __future__ import annotations


class TransicionInvalida(Exception):
    pass


class CobroYaPagado(TransicionInvalida):
    pass


class CobroAnulado(TransicionInvalida):
    pass


class EstadoCobro:
    nombre: str
    permite_salida: bool

    def pagar(self) -> EstadoCobro:
        raise NotImplementedError

    def anular(self) -> EstadoCobro:
        raise NotImplementedError


class Pendiente(EstadoCobro):
    nombre = "PENDIENTE"
    permite_salida = False

    def pagar(self) -> EstadoCobro:
        return PAGADO

    def anular(self) -> EstadoCobro:
        return ANULADO


class Pagado(EstadoCobro):
    nombre = "PAGADO"
    permite_salida = True

    def pagar(self) -> EstadoCobro:
        raise CobroYaPagado("El cobro ya está pagado")

    def anular(self) -> EstadoCobro:
        raise TransicionInvalida("Un cobro pagado no se puede anular")


class Anulado(EstadoCobro):
    nombre = "ANULADO"
    permite_salida = True

    def pagar(self) -> EstadoCobro:
        raise CobroAnulado("El cobro está anulado")

    def anular(self) -> EstadoCobro:
        raise CobroAnulado("El cobro ya está anulado")


PENDIENTE = Pendiente()
PAGADO = Pagado()
ANULADO = Anulado()
_ESTADOS = {estado.nombre: estado for estado in (PENDIENTE, PAGADO, ANULADO)}


def estado_de(nombre: str) -> EstadoCobro:
    return _ESTADOS[nombre]