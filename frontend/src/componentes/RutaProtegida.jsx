import { Navigate, Outlet } from "react-router-dom";
import { obtenerSesion } from "../auth/sesion.js";
import { inicioDe } from "../auth/rutas.js";

// Deja pasar solo si hay sesión y el rol coincide con el de la pantalla.
export default function RutaProtegida({ rol }) {
  const sesion = obtenerSesion();
  if (!sesion) return <Navigate to="/login" replace />;
  if (rol && sesion.rol !== rol) return <Navigate to={inicioDe(sesion.rol)} replace />;
  return <Outlet />;
}
