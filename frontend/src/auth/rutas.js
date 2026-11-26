// Qué pantallas ve cada rol (F-10). El backend también valida el rol en cada endpoint:
// el operador recibe 403 en administración y consultas.
export const PANTALLAS = [
  { ruta: "/entrada", nombre: "Carril de entrada", rol: "OPERADOR" },
  { ruta: "/caja", nombre: "Caja", rol: "OPERADOR" },
  { ruta: "/salida", nombre: "Carril de salida", rol: "OPERADOR" },
  { ruta: "/validacion", nombre: "Validación manual", rol: "OPERADOR" },
  { ruta: "/consultas", nombre: "Consultas", rol: "ADMIN" },
  { ruta: "/admin", nombre: "Administración", rol: "ADMIN" },
];

export function pantallasDe(rol) {
  return PANTALLAS.filter((p) => p.rol === rol);
}

export function inicioDe(rol) {
  return pantallasDe(rol)[0]?.ruta ?? "/login";
}
