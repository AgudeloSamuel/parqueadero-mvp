import { Navigate, Route, Routes } from "react-router-dom";
import Login from "./paginas/Login.jsx";
import Pendiente from "./paginas/Pendiente.jsx";
import Plantilla from "./componentes/Plantilla.jsx";
import RutaProtegida from "./componentes/RutaProtegida.jsx";
import { obtenerSesion } from "./auth/sesion.js";
import { inicioDe } from "./auth/rutas.js";

function Inicio() {
  const sesion = obtenerSesion();
  return <Navigate to={sesion ? inicioDe(sesion.rol) : "/login"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Plantilla />}>
        <Route element={<RutaProtegida rol="OPERADOR" />}>
          <Route path="/entrada" element={<Pendiente titulo="Carril de entrada" historia="la HU-02" />} />
          <Route path="/caja" element={<Pendiente titulo="Caja" historia="la búsqueda de cobros por placa" />} />
          <Route path="/salida" element={<Pendiente titulo="Carril de salida" historia="la HU-06" />} />
          <Route path="/validacion" element={<Pendiente titulo="Validación manual" historia="la HU-07" />} />
        </Route>
        <Route element={<RutaProtegida rol="ADMIN" />}>
          <Route path="/consultas" element={<Pendiente titulo="Consultas" historia="la HU-11" />} />
          <Route path="/admin" element={<Pendiente titulo="Administración" historia="la configuración (HU-09 y HU-10)" />} />
        </Route>
      </Route>
      <Route path="*" element={<Inicio />} />
    </Routes>
  );
}
