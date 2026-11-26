// Formatos de pantalla en español de Colombia.
export function pesos(valor) {
  return `$${Number(valor).toLocaleString("es-CO")}`;
}

export function hora(fechaIso) {
  return new Date(fechaIso).toLocaleTimeString("es-CO", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "America/Bogota",
  });
}

const TIPOS = { CARRO: "Carro", MOTO: "Moto" };
export function tipoVehiculo(tipo) {
  return TIPOS[tipo] ?? "Sin identificar";
}

// El backend envía valores como "$3850"; aquí se muestran como "$3.850".
export function motivoLegible(motivo = "") {
  return motivo.replace(/\$(\d{4,})/g, (_, n) => pesos(n));
}

export function saludo(fecha = new Date()) {
  const h = fecha.getHours();
  if (h < 12) return "Buenos días";
  if (h < 19) return "Buenas tardes";
  return "Buenas noches";
}
