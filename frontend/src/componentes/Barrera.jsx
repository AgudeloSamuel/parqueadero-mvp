import { useEffect, useState } from "react";
import { motivoLegible } from "../formato.js";

// Indicador visual de la barrera (hardware simulado).
// Verde: ABIERTA. Rojo: CERRADA o LLENO. Ámbar: PENDIENTE_VALIDACION.
const ESTILOS = {
  ABIERTA: { clase: "barrera-verde", texto: "Abierta", titulo: "Barrera abierta" },
  CERRADA: { clase: "barrera-roja", texto: "Cerrada", titulo: "Barrera cerrada" },
  LLENO: { clase: "barrera-roja", texto: "Lleno", titulo: "Parqueadero lleno" },
  PENDIENTE_VALIDACION: { clase: "barrera-ambar", texto: "Pendiente", titulo: "Pendiente de validación" },
};

export function estiloBarrera(estado) {
  return ESTILOS[estado] ?? { clase: "barrera-roja", texto: estado, titulo: `Barrera: ${estado}` };
}

// Estado de la barrera como etiqueta, para las tablas.
export function EstadoBarrera({ estado }) {
  const { clase, texto } = estiloBarrera(estado);
  return <span className={`etiqueta ${clase}`}>{texto}</span>;
}

// Dibujo de la barrera: el brazo sube cuando abre y baja cuando cierra.
export function DibujoBarrera({ estado }) {
  // Empieza cerrada y se mueve al estado real después de montar, para que se vea el movimiento.
  const [visible, setVisible] = useState("CERRADA");
  useEffect(() => {
    const id = requestAnimationFrame(() => setVisible(estado));
    return () => cancelAnimationFrame(id);
  }, [estado]);
  const abierta = visible === "ABIERTA";
  return (
    <svg className={`dibujo-barrera ${estiloBarrera(estado).clase}`} viewBox="0 0 160 170" aria-hidden="true">
      <defs>
        <pattern id="franjas" width="22" height="12" patternUnits="userSpaceOnUse">
          <rect width="11" height="12" className="franja-color" />
          <rect x="11" width="11" height="12" className="franja-clara" />
        </pattern>
      </defs>
      <rect x="0" y="162" width="160" height="4" rx="2" className="suelo" />
      <g className={`brazo ${abierta ? "brazo-arriba" : ""}`}>
        <rect x="24" y="128" width="130" height="12" rx="6" fill="url(#franjas)" />
        <rect x="24" y="128" width="130" height="12" rx="6" className="brazo-borde" />
      </g>
      <rect x="10" y="120" width="28" height="44" rx="9" className="poste" />
      <circle cx="24" cy="134" r="5" className="tornillo" />
      <circle cx="24" cy="153" r="5" className={`luz ${estado === "PENDIENTE_VALIDACION" ? "luz-parpadea" : ""}`} />
    </svg>
  );
}

export default function Barrera({ estado, motivo }) {
  const { clase, titulo } = estiloBarrera(estado);
  return (
    <div className={`barrera ${clase}`} role="status">
      <DibujoBarrera estado={estado} />
      <div className="barrera-texto">
        <strong>{titulo}</strong>
        <span>{motivoLegible(motivo)}</span>
      </div>
    </div>
  );
}
