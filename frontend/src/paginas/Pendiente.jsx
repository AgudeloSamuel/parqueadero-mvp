import { IlustracionVacia } from "../componentes/Ilustraciones.jsx";

// Pantalla temporal mientras se construye y se conecta con su historia.
export default function Pendiente({ titulo, historia }) {
  return (
    <>
      <header className="encabezado">
        <h1>{titulo}</h1>
      </header>
      <section className="tarjeta vacio vacio-grande">
        <IlustracionVacia />
        <p className="vacio-titulo">Esta pantalla viene en camino</p>
        <p className="suave">Se conecta con el sistema cuando esté lista {historia}.</p>
      </section>
    </>
  );
}
