// Placa colombiana: fondo amarillo, letras negras y la ciudad debajo.
export default function Placa({ placa, ciudad = "MANIZALES", tamano = "normal" }) {
  const limpia = (placa || "").toUpperCase();
  const texto = limpia.length > 3 ? `${limpia.slice(0, 3)} ${limpia.slice(3)}` : limpia;
  return (
    <div className={`placa placa-${tamano}`} aria-label={`Placa ${limpia}`}>
      <span className="placa-numero">{texto}</span>
      <span className="placa-ciudad">{ciudad}</span>
    </div>
  );
}
