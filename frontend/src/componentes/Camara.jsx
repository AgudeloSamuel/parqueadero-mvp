import { useEffect, useRef, useState } from "react";
import { Camera, CameraSlash, Aperture } from "@phosphor-icons/react";

// HU-13: muestra la cámara del PC en vivo y captura una foto de la placa.
// La foto se entrega como archivo JPG para enviarla a POST /carril/entrada/imagen.
const MENSAJES = {
  NotAllowedError: "No diste permiso para usar la cámara. Actívalo en el navegador y vuelve a intentarlo.",
  NotFoundError: "No se encontró ninguna cámara conectada.",
};

export default function Camara({ onCaptura, deshabilitado }) {
  const video = useRef(null);
  const flujo = useRef(null);
  const [encendida, setEncendida] = useState(false);
  const [error, setError] = useState("");

  function apagar() {
    flujo.current?.getTracks().forEach((pista) => pista.stop());
    flujo.current = null;
    setEncendida(false);
  }

  // Al salir de la pantalla se apaga la cámara.
  useEffect(() => apagar, []);

  async function encender() {
    setError("");
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Este navegador no permite usar la cámara.");
      return;
    }
    try {
      flujo.current = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      video.current.srcObject = flujo.current;
      await video.current.play();
      setEncendida(true);
    } catch (e) {
      apagar();
      setError(MENSAJES[e.name] ?? "No se pudo encender la cámara.");
    }
  }

  function capturar() {
    const v = video.current;
    const lienzo = document.createElement("canvas");
    lienzo.width = v.videoWidth || 640;
    lienzo.height = v.videoHeight || 480;
    lienzo.getContext("2d").drawImage(v, 0, 0, lienzo.width, lienzo.height);
    lienzo.toBlob(
      (foto) => onCaptura(new File([foto], "placa.jpg", { type: "image/jpeg" })),
      "image/jpeg",
      0.9,
    );
  }

  return (
    <div className="camara">
      <div className="camara-marco">
        <video ref={video} className="camara-video" muted playsInline hidden={!encendida} aria-label="Cámara en vivo" />
        {encendida ? (
          <span className="camara-guia" aria-hidden="true" />
        ) : (
          <div className="camara-apagada">
            <CameraSlash size={28} aria-hidden="true" />
            <span>Cámara apagada</span>
          </div>
        )}
      </div>
      <div className="fila">
        {encendida ? (
          <>
            <button type="button" className="boton boton-primario" onClick={capturar} disabled={deshabilitado}>
              <Aperture size={18} weight="bold" aria-hidden="true" />
              Capturar placa
            </button>
            <button type="button" className="boton" onClick={apagar}>
              Apagar cámara
            </button>
          </>
        ) : (
          <button type="button" className="boton boton-primario" onClick={encender}>
            <Camera size={18} weight="bold" aria-hidden="true" />
            Encender cámara
          </button>
        )}
      </div>
      {error && <p className="aviso aviso-error">{error}</p>}
    </div>
  );
}
