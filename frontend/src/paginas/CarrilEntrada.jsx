import { useState } from "react";
import { Camera, Image, Keyboard } from "@phosphor-icons/react";
import { api } from "../api/cliente.js";
import Camara from "../componentes/Camara.jsx";
import { Historial, Resultado } from "../componentes/Resultado.jsx";
import { pesos } from "../formato.js";

const SEDE_ID = Number(import.meta.env.VITE_SEDE_ID ?? 1);

const MODOS = [
  { id: "camara", nombre: "Cámara", Icono: Camera },
  { id: "foto", nombre: "Foto", Icono: Image },
  { id: "manual", nombre: "Manual", Icono: Keyboard },
];

// HU-02 y HU-13: registrar el ingreso por placa. La placa se lee con la cámara
// del PC (el OCR del backend lee la foto), desde una imagen guardada o con el simulador.
export default function CarrilEntrada() {
  const [modo, setModo] = useState("camara");
  const [placa, setPlaca] = useState("");
  const [confianza, setConfianza] = useState("0.95");
  const [imagen, setImagen] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [historial, setHistorial] = useState([]);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);

  async function registrar(leer) {
    setError("");
    setCargando(true);
    try {
      const datos = await leer();
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

  function porPlaca(evento) {
    evento.preventDefault();
    registrar(() => api.registrarEntrada(placa, Number(confianza), SEDE_ID));
  }

  function porImagen(archivo) {
    if (archivo) registrar(() => api.registrarEntradaImagen(archivo, SEDE_ID));
  }

  const indice = MODOS.findIndex((m) => m.id === modo);

  return (
    <>
      <header className="encabezado">
        <h1>Carril de entrada</h1>
        <p className="suave">Lee la placa y el sistema decide si la barrera abre.</p>
      </header>
      <div className="columnas">
        <section className="tarjeta">
          <div className="tarjeta-cabeza">
            <h2>Lectura de placa</h2>
            <div className="segmentos" role="tablist" aria-label="Forma de leer la placa" style={{ "--indice": indice, "--opciones": MODOS.length }}>
              <span className="segmentos-indicador" aria-hidden="true" />
              {MODOS.map(({ id, nombre, Icono }) => (
                <button
                  key={id}
                  type="button"
                  role="tab"
                  aria-selected={modo === id}
                  className="segmento"
                  onClick={() => setModo(id)}
                >
                  <Icono size={16} weight="bold" aria-hidden="true" />
                  {nombre}
                </button>
              ))}
            </div>
          </div>

          {modo === "camara" && <Camara onCaptura={porImagen} deshabilitado={cargando} />}

          {modo === "foto" && (
            <div className="pila">
              <label className="campo">
                Foto de la placa
                <input type="file" accept="image/png,image/jpeg" onChange={(e) => setImagen(e.target.files[0] ?? null)} />
              </label>
              <div className="fila">
                <button type="button" className="boton boton-primario" onClick={() => porImagen(imagen)} disabled={!imagen || cargando}>
                  Leer imagen
                </button>
              </div>
            </div>
          )}

          {modo === "manual" && (
            <form className="pila" onSubmit={porPlaca}>
              <p className="suave">Úsalo para probar el carril sin cámara (simulador).</p>
              <div className="fila">
                <label className="campo campo-placa">
                  Placa
                  <input value={placa} onChange={(e) => setPlaca(e.target.value)} placeholder="ABC123" required />
                </label>
                <label className="campo campo-corto">
                  Confianza de lectura
                  <input type="number" min="0" max="1" step="0.01" value={confianza} onChange={(e) => setConfianza(e.target.value)} required />
                </label>
              </div>
              <div className="fila">
                <button type="submit" className="boton boton-primario" disabled={cargando}>
                  Registrar ingreso
                </button>
              </div>
            </form>
          )}

          {error && <p className="aviso aviso-error">{error}</p>}
        </section>

        <section className="tarjeta" aria-live="polite">
          <h2>Resultado</h2>
          <Resultado resultado={resultado} vacio="Aquí verás la placa y la barrera cuando registres una lectura.">
            {resultado && (
              <>
                <dt>Cobro del día</dt>
                <dd>{resultado.cobro ? `${pesos(resultado.cobro.valor)} (${resultado.cobro.estado.toLowerCase()})` : "Sin cobro"}</dd>
              </>
            )}
          </Resultado>
        </section>
      </div>

      <section className="tarjeta">
        <h2>Últimos ingresos</h2>
        <Historial filas={historial} vacio="Todavía no hay ingresos en este turno." />
      </section>
    </>
  );
}
