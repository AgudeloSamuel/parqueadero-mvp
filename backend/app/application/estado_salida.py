from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from app.domain.puertos import RepositorioCobros


def formato_pesos(valor: int) -> str:
    return f"${valor:,}".replace(",", ".")


class ConsultaSalida:
    def __init__(
        self,
        cobros: RepositorioCobros,
        ultima_entrada: Callable[[str, int], datetime | None],
    ) -> None:
        self.cobros = cobros
        self.ultima_entrada = ultima_entrada

    def estado_para_salida(
        self, placa: str, sede_id: int, fecha_hora: datetime
    ) -> tuple[bool, str]:
        entrada = self.ultima_entrada(placa, sede_id)
        if entrada is None:
            dia = fecha_hora.date()
        elif entrada.tzinfo is not None and fecha_hora.tzinfo is not None:
            dia = entrada.astimezone(fecha_hora.tzinfo).date()
        else:
            dia = entrada.date()

        cobro = self.cobros.buscar_del_dia(placa, sede_id, dia)
        if cobro is None:
            return True, "Sin cobro"
        if cobro.estado == "ANULADO":
            return False, "Cobro anulado"
        if not cobro.ciclo.permite_salida:
            return False, f"Pago pendiente: {formato_pesos(cobro.valor)}"
        return True, "Pago verificado"
