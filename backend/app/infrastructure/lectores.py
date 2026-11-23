import csv
import io
import subprocess
from typing import Literal, overload

from PIL import Image, UnidentifiedImageError

from app.domain.ingreso import LecturaInvalida, LecturaPlaca, normalizar_placa


class OCRNoDisponible(RuntimeError):
    pass


class LectorSimulado:
    def leer(self, placa: str, confianza: float, sede_id: int) -> LecturaPlaca:
        return LecturaPlaca(normalizar_placa(placa), confianza, sede_id)


class LectorOCR:
    def leer(self, imagen: bytes, sede_id: int) -> LecturaPlaca:
        try:
            with Image.open(io.BytesIO(imagen), formats=["PNG", "JPEG"]) as archivo:
                if archivo.width * archivo.height > 12_000_000:
                    raise LecturaInvalida("La imagen supera los 12 megapíxeles")
                archivo.verify()
        except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
            raise LecturaInvalida("La imagen debe ser un PNG o JPEG válido") from exc

        try:
            resultado = subprocess.run(
                ["tesseract", "stdin", "stdout", "-l", "eng", "--psm", "7", "tsv"],
                input=imagen,
                capture_output=True,
                check=True,
                timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise OCRNoDisponible("El lector de imágenes no está disponible") from exc
        except subprocess.CalledProcessError as exc:
            raise LecturaInvalida("No se pudo leer la imagen") from exc

        filas = csv.DictReader(io.StringIO(resultado.stdout.decode("utf-8")), delimiter="\t")
        palabras = [
            (fila["text"], float(fila["conf"]))
            for fila in filas
            if fila["level"] == "5" and fila["text"] and fila["text"].strip()
        ]
        if not palabras:
            raise LecturaInvalida("No se pudo leer una placa en la imagen")
        placa = normalizar_placa("".join(texto for texto, _ in palabras))
        confianza = min(puntaje for _, puntaje in palabras) / 100
        return LecturaPlaca(placa, confianza, sede_id)


class FabricaLector:
    @overload
    @staticmethod
    def crear(origen: Literal["simulador"]) -> LectorSimulado: ...

    @overload
    @staticmethod
    def crear(origen: Literal["imagen"]) -> LectorOCR: ...

    @staticmethod
    def crear(origen: Literal["simulador", "imagen"]) -> LectorSimulado | LectorOCR:
        lectores = {"simulador": LectorSimulado, "imagen": LectorOCR}
        return lectores[origen]()
