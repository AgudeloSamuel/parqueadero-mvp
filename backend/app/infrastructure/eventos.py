from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.domain.ingreso import EventoEntrada
from app.domain.salida import EventoSalida
from app.infrastructure.db import EventoDB, motor_db


def consultar_pendientes(sesion: Session, sede_id: int | None) -> list[EventoDB]:
    consulta = select(EventoDB).where(
        EventoDB.tipo == "ENTRADA", EventoDB.barrera == "PENDIENTE_VALIDACION"
    )
    if sede_id is not None:
        consulta = consulta.where(EventoDB.sede_id == sede_id)
    return list(sesion.scalars(consulta.order_by(EventoDB.fecha_hora, EventoDB.id)))


def bloquear_pendiente(evento_id: int, sesion: Session) -> EventoDB | None:
    # El UPDATE condiciona la toma del bloqueo a que siga pendiente, también en SQLite.
    return sesion.scalar(
        update(EventoDB)
        .where(
            EventoDB.id == evento_id,
            EventoDB.tipo == "ENTRADA",
            EventoDB.barrera == "PENDIENTE_VALIDACION",
        )
        .values(barrera=EventoDB.barrera)
        .returning(EventoDB)
    )


def resolver_pendiente(fila: EventoDB, evento: EventoEntrada) -> int:
    fila.placa_leida = fila.placa
    fila.placa = evento.lectura.placa
    fila.tipo_vehiculo = evento.tipo_vehiculo
    fila.barrera = evento.barrera
    fila.motivo = evento.motivo
    fila.lectura_manual = True
    fila.validada_por = evento.lectura.validada_por
    fila.validada_en = evento.fecha_hora
    return fila.id


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
