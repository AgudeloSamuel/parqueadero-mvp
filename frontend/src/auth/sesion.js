// Guarda la sesión (token JWT, rol y usuario) en sessionStorage:
// se borra al cerrar la pestaña y no se comparte entre pestañas.
const CLAVE = "parqueadero.sesion";

export function guardarSesion({ token, rol, usuario }) {
  sessionStorage.setItem(CLAVE, JSON.stringify({ token, rol, usuario }));
}

export function obtenerSesion() {
  try {
    const guardada = JSON.parse(sessionStorage.getItem(CLAVE));
    return guardada?.token && guardada?.rol ? guardada : null;
  } catch {
    return null;
  }
}

export function cerrarSesion() {
  sessionStorage.removeItem(CLAVE);
}
