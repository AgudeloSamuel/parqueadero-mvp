from sqlalchemy.orm import Session

from app.domain.ingreso import EventoEntrada
from app.domain.salida import EventoSalida
from app.infrastructure.db import EventoDB, motor_db


def _guardar(fila: EventoDB, sesion: Session | None) -> int:
    if sesion is None:
        with Session(motor_db()) as propia, propia.begin():
            return _guardar(fila, propia)
    sesion.add(fila)
    sesion.flush()
    return fila.id


def guardar_entrada(evento: EventoEntrada, sesion: Session | None = None) -> int:
    fila = EventoDB(
        tipo="ENTRADA",
        placa=evento.lectura.placa,
        confianza=evento.lectura.confianza,
        sede_id=evento.lectura.sede_id,
        fecha_hora=evento.fecha_hora,
        tipo_vehiculo=evento.tipo_vehiculo,
        barrera=evento.barrera,
        motivo=evento.motivo,
    )
    return _guardar(fila, sesion)


def guardar_salida(evento: EventoSalida, sesion: Session | None = None) -> int:
    fila = EventoDB(
        tipo="SALIDA",
        placa=evento.placa,
        confianza=1.0,  # La placa se recibe directamente en el carril de salida simulado.
        sede_id=evento.sede_id,
        fecha_hora=evento.fecha_hora,
        tipo_vehiculo=evento.tipo_vehiculo,
        barrera=evento.barrera,
        motivo=evento.motivo,
    )
    return _guardar(fila, sesion)
