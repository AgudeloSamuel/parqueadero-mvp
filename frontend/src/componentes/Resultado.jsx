import Barrera, { EstadoBarrera } from "./Barrera.jsx";
import { IlustracionVacia } from "./Ilustraciones.jsx";
import Placa from "./Placa.jsx";
import { hora, motivoLegible, tipoVehiculo } from "../formato.js";

// Panel con el resultado de la última lectura: placa, barrera y datos.
export function Resultado({ resultado, vacio, children }) {
  if (!resultado) {
    return (
      <div className="vacio">
        <IlustracionVacia />
        <p className="suave">{vacio}</p>
      </div>
    );
  }
  return (
    <div className="resultado" key={resultado.evento_id}>
      <Placa placa={resultado.placa} />
      <Barrera estado={resultado.barrera} motivo={resultado.motivo} />
      <dl className="datos">
        <dt>Vehículo</dt>
        <dd>{tipoVehiculo(resultado.tipo_vehiculo)}</dd>
        <dt>Hora</dt>
        <dd>{hora(resultado.fecha_hora)}</dd>
        {children}
      </dl>
    </div>
  );
}

// Tabla con las últimas lecturas del turno (se guardan solo en esta pantalla).
export function Historial({ filas, vacio }) {
  if (filas.length === 0) return <p className="suave historial-vacio">{vacio}</p>;
  return (
    <div className="tabla-envoltura">
      <table>
        <thead>
          <tr>
            <th>Placa</th>
            <th>Vehículo</th>
            <th>Hora</th>
            <th>Barrera</th>
            <th>Motivo</th>
          </tr>
        </thead>
        <tbody>
          {filas.map((h) => (
            <tr key={h.evento_id}>
              <td className="celda-placa">{h.placa}</td>
              <td>{tipoVehiculo(h.tipo_vehiculo)}</td>
              <td className="numero">{hora(h.fecha_hora)}</td>
              <td>
                <EstadoBarrera estado={h.barrera} />
              </td>
              <td>{motivoLegible(h.motivo)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
