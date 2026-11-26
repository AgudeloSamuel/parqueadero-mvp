import { useState } from "react";
import { api } from "../api/cliente.js";
import { Historial, Resultado } from "../componentes/Resultado.jsx";

const SEDE_ID = Number(import.meta.env.VITE_SEDE_ID ?? 1);

// HU-06: validar la salida. El backend decide si la barrera abre:
// cobro pagado o sin cobro → ABIERTA; cobro pendiente → CERRADA con el valor.
export default function CarrilSalida() {
  const [placa, setPlaca] = useState("");
  const [resultado, setResultado] = useState(null);
  const [historial, setHistorial] = useState([]);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);

  async function validar(evento) {
    evento.preventDefault();
    setError("");
    setCargando(true);
    try {
      const datos = await api.registrarSalida(placa, SEDE_ID);
      setResultado(datos);
      setHistorial((anteriores) => [datos, ...anteriores].slice(0, 10));
      setPlaca("");
    } catch (e) {
      setResultado(null);
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }

  return (
    <>
      <header className="encabezado">
        <h1>Carril de salida</h1>
        <p className="suave">La salida funciona las 24 horas.</p>
      </header>
      <div className="columnas">
        <section className="tarjeta">
          <h2>Lectura de placa</h2>
          <form className="pila" onSubmit={validar}>
            <label className="campo campo-placa">
              Placa
              <input value={placa} onChange={(e) => setPlaca(e.target.value)} placeholder="ABC123" required />
            </label>
            <div className="fila">
              <button type="submit" className="boton boton-primario" disabled={cargando}>
                Validar salida
              </button>
            </div>
          </form>
          {error && <p className="aviso aviso-error">{error}</p>}
        </section>

        <section className="tarjeta" aria-live="polite">
          <h2>Resultado</h2>
          <Resultado resultado={resultado} vacio="Escribe una placa para saber si el carro puede salir." />
          {resultado?.barrera === "CERRADA" && <p className="aviso aviso-info">El conductor debe pasar por la caja.</p>}
        </section>
      </div>

      <section className="tarjeta">
        <h2>Salidas recientes</h2>
        <Historial filas={historial} vacio="Todavía no hay salidas en este turno." />
      </section>
    </>
  );
}
