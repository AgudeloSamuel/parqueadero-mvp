// Tema claro u oscuro. Por defecto sigue al sistema; si el operador lo cambia,
// se recuerda en este navegador.
const CLAVE = "parqueadero.tema";

export function temaGuardado() {
  try {
    const t = localStorage.getItem(CLAVE);
    return t === "claro" || t === "oscuro" ? t : null;
  } catch {
    return null;
  }
}

export function temaEfectivo() {
  const guardado = temaGuardado();
  if (guardado) return guardado;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "oscuro" : "claro";
}

export function aplicarTema(tema) {
  document.documentElement.dataset.tema = tema;
  try {
    localStorage.setItem(CLAVE, tema);
  } catch {
    // Sin almacenamiento: el cambio dura hasta recargar.
  }
}

export function iniciarTema() {
  const guardado = temaGuardado();
  if (guardado) document.documentElement.dataset.tema = guardado;
}
