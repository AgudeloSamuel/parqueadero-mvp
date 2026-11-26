// Ilustraciones hechas en código (SVG). Sin imágenes externas.

// Parqueadero visto desde arriba: puestos demarcados y algunos carros.
// La distribución es fija para que la imagen sea estable en cada carga.
const PUESTOS = [1, 0, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1];
const TONOS = ["carro-1", "carro-2", "carro-3", "carro-4"];

export function IlustracionParqueadero() {
  return (
    <svg className="ilustracion-parqueadero" viewBox="0 0 360 300" aria-hidden="true">
      <rect x="10" y="10" width="340" height="280" rx="28" className="asfalto" />
      <rect x="26" y="142" width="308" height="16" rx="8" className="via" />
      {[0, 1].map((fila) =>
        Array.from({ length: 6 }).map((_, col) => {
          const i = fila * 6 + col;
          const x = 30 + col * 50;
          const y = fila === 0 ? 30 : 170;
          return (
            <g key={i}>
              <path
                d={fila === 0 ? `M${x} ${y + 100} V${y} H${x + 46} V${y + 100}` : `M${x} ${y} V${y + 100} H${x + 46} V${y}`}
                className="puesto"
              />
              {PUESTOS[i] === 1 && (
                <g className="carro" style={{ "--i": i }}>
                  <rect x={x + 8} y={y + 14} width="30" height="72" rx="12" className={TONOS[i % 4]} />
                  <rect x={x + 12} y={y + 26} width="22" height="16" rx="5" className="vidrio" />
                  <rect x={x + 12} y={y + 60} width="22" height="12" rx="5" className="vidrio" />
                </g>
              )}
            </g>
          );
        }),
      )}
      <circle cx="320" cy="150" r="5" className="flecha-punto" />
    </svg>
  );
}

// Carro de línea suave para los estados vacíos.
export function IlustracionVacia() {
  return (
    <svg className="ilustracion-vacia" viewBox="0 0 160 90" aria-hidden="true">
      <rect x="6" y="78" width="148" height="4" rx="2" className="suelo" />
      <path d="M26 64 L34 40 Q38 30 50 30 L106 30 Q118 30 124 40 L136 64 Q140 70 134 72 L26 72 Q20 70 26 64 Z" className="carroceria" />
      <path d="M46 44 L52 36 L76 36 L76 50 L42 50 Z M84 36 L104 36 Q110 36 114 44 L118 50 L84 50 Z" className="ventana" />
      <circle cx="48" cy="74" r="10" className="llanta" />
      <circle cx="114" cy="74" r="10" className="llanta" />
    </svg>
  );
}
