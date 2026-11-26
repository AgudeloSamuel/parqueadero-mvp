import { cerrarSesion, obtenerSesion } from "../auth/sesion.js";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

export class ErrorApi extends Error {
  constructor(status, mensaje) {
    super(mensaje);
    this.status = status;
  }
}

// FastAPI devuelve {"detail": "texto"} o, en errores 422 de validación,
// {"detail": [{msg: "..."}, ...]}. Esta función deja siempre un texto.
export function mensajeDeError(cuerpo, status) {
  const detalle = cuerpo?.detail;
  if (typeof detalle === "string") return detalle;
  if (Array.isArray(detalle)) return detalle.map((d) => d.msg).join(". ");
  if (status === 0) return "No hay conexión con el servidor. ¿Está corriendo el backend?";
  return `Error ${status} del servidor`;
}

// Cliente HTTP único: agrega el token y traduce los errores.
export async function pedir(ruta, { metodo = "GET", cuerpo, encabezados = {} } = {}) {
  const sesion = obtenerSesion();
  const headers = { ...encabezados };
  if (sesion) headers.Authorization = `Bearer ${sesion.token}`;
  let body = cuerpo;
  if (cuerpo && !(cuerpo instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(cuerpo);
  }

  let respuesta;
  try {
    respuesta = await fetch(`${API_URL}${ruta}`, { method: metodo, headers, body });
  } catch {
    throw new ErrorApi(0, mensajeDeError(null, 0));
  }

  const datos = await respuesta.json().catch(() => null);
  if (!respuesta.ok) {
    // Token vencido o inválido: se cierra la sesión para volver al login.
    if (respuesta.status === 401 && sesion) cerrarSesion();
    throw new ErrorApi(respuesta.status, mensajeDeError(datos, respuesta.status));
  }
  return datos;
}

export const api = {
  login: (username, password) =>
    pedir("/auth/login", { metodo: "POST", cuerpo: { username, password } }),
  registrarEntrada: (placa, confianza, sedeId) =>
    pedir("/carril/entrada", { metodo: "POST", cuerpo: { placa, confianza, sede_id: sedeId } }),
  registrarEntradaImagen: (archivo, sedeId) => {
    const formulario = new FormData();
    formulario.append("imagen", archivo);
    formulario.append("sede_id", String(sedeId));
    return pedir("/carril/entrada/imagen", { metodo: "POST", cuerpo: formulario });
  },
};
