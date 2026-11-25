import io
import os
from functools import lru_cache
from threading import Lock
from typing import Literal, overload

from PIL import Image, ImageOps

from app.domain.ingreso import LecturaInvalida, LecturaPlaca
from app.domain.vehiculo import Clasificador, normalizar_placa

_candado_ocr = Lock()
_clasificador = Clasificador()


class OCRNoDisponible(RuntimeError):
    pass


class LectorCamaraDesactivado(ValueError):
    pass


class LectorSimulado:
    def leer(self, placa: str, confianza: float, sede_id: int) -> LecturaPlaca:
        return LecturaPlaca(normalizar_placa(placa), confianza, sede_id)


@lru_cache(maxsize=1)
def motor_easyocr():
    from easyocr import Reader

    return Reader(["en"], gpu=False, verbose=False)


class LectorOCR:
    def leer(self, imagen: bytes, sede_id: int) -> LecturaPlaca:
        try:
            with Image.open(io.BytesIO(imagen), formats=["PNG", "JPEG"]) as archivo:
                if archivo.width * archivo.height > 12_000_000:
                    raise LecturaInvalida("La imagen supera los 12 megapíxeles")
                orientada = ImageOps.exif_transpose(archivo).convert("RGB")
                orientada.thumbnail((1920, 1920))
                contenido = io.BytesIO()
                orientada.save(contenido, format="PNG")
        except (OSError, SyntaxError, Image.DecompressionBombError) as exc:
            raise LecturaInvalida("La imagen debe ser un PNG o JPEG válido") from exc

        try:
            with _candado_ocr:
                lecturas = motor_easyocr().readtext(
                    contenido.getvalue(),
                    allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 -",
                )
        except (ImportError, OSError, RuntimeError) as exc:
            raise OCRNoDisponible("EasyOCR no está disponible") from exc

        candidatos = [
            (normalizar_placa(texto), float(confianza))
            for _, texto, confianza in lecturas
        ]
        aptos = (
            (placa, confianza)
            for placa, confianza in candidatos
            if _clasificador.clasificar(placa) is not None and 0 <= confianza <= 1
        )
        placa, confianza = max(aptos, key=lambda lectura: lectura[1], default=(None, 0.0))
        return LecturaPlaca(placa, confianza, sede_id)


class FabricaLector:
    @overload
    @staticmethod
    def crear(origen: Literal["simulador"]) -> LectorSimulado: ...

    @overload
    @staticmethod
    def crear(origen: Literal["camara"]) -> LectorOCR: ...

    @overload
    @staticmethod
    def crear(origen: None = None) -> LectorSimulado | LectorOCR: ...

    @staticmethod
    def crear(origen: Literal["simulador", "camara"] | None = None) -> LectorSimulado | LectorOCR:
        modo = origen or os.environ.get("LECTOR_PLACAS", "camara")
        if modo == "simulador":
            return LectorSimulado()
        if modo == "camara":
            return LectorOCR()
        raise OCRNoDisponible("LECTOR_PLACAS debe ser camara o simulador")

    @staticmethod
    def para_imagen() -> LectorOCR:
        lector = FabricaLector.crear()
        if isinstance(lector, LectorSimulado):
            raise LectorCamaraDesactivado(
                "El lector está en modo simulador. Usa POST /api/v1/carril/entrada."
            )
        return lector
