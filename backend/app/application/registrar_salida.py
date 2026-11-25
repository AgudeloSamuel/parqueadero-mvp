from collections.abc import Callable
from datetime import datetime

from app.application.estado_salida import ConsultaSalida
from app.domain.ingreso import clasificar_placa
from app.domain.salida import EventoSalida
from app.domain.vehiculo import normalizar_placa


class RegistrarSalida:
    def __init__(
        self,
        consulta: ConsultaSalida,
        guardar: Callable[[EventoSalida], int],
        ahora: Callable[[], datetime],
    ) -> None:
        self.consulta = consulta
        self.guardar = guardar
        self.ahora = ahora

    def ejecutar(self, placa: str, sede_id: int) -> tuple[int, EventoSalida]:
        placa = normalizar_placa(placa)
        tipo = clasificar_placa(placa)
        momento = self.ahora()
        permitida, motivo = self.consulta.estado_para_salida(placa, sede_id, momento)
        evento = EventoSalida(
            placa, sede_id, momento, tipo, "ABIERTA" if permitida else "CERRADA", motivo
        )
        return self.guardar(evento), evento
