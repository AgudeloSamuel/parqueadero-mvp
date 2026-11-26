import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { Moon, SignOut, Sun } from "@phosphor-icons/react";
import { cerrarSesion, obtenerSesion } from "../auth/sesion.js";
import { pantallasDe } from "../auth/rutas.js";
import { aplicarTema, temaEfectivo } from "../tema.js";

export default function Menu() {
  const navegar = useNavigate();
  const sesion = obtenerSesion();
  const [tema, setTema] = useState(temaEfectivo);

  function salir() {
    cerrarSesion();
    navegar("/login", { replace: true });
  }

  function cambiarTema() {
    const nuevo = tema === "oscuro" ? "claro" : "oscuro";
    aplicarTema(nuevo);
    setTema(nuevo);
  }

  return (
    <header className="menu">
      <span className="marca">
        <span className="marca-signo" aria-hidden="true">P</span>
        Parqueadero
      </span>
      <nav className="menu-pestanas">
        {pantallasDe(sesion?.rol).map((p) => (
          <NavLink key={p.ruta} to={p.ruta} className="pestana">
            {p.nombre}
          </NavLink>
        ))}
      </nav>
      <div className="menu-derecha">
        <button
          type="button"
          className="boton-icono"
          onClick={cambiarTema}
          aria-label={tema === "oscuro" ? "Usar modo claro" : "Usar modo oscuro"}
          title={tema === "oscuro" ? "Modo claro" : "Modo oscuro"}
        >
          {tema === "oscuro" ? <Sun size={18} weight="bold" /> : <Moon size={18} weight="bold" />}
        </button>
        <span className="usuario">
          <span className="usuario-avatar" aria-hidden="true">{sesion?.usuario?.[0]?.toUpperCase()}</span>
          <span>
            <span className="usuario-nombre">{sesion?.usuario}</span>
            <span className="usuario-rol">{sesion?.rol === "ADMIN" ? "Administrador" : "Operador"}</span>
          </span>
        </span>
        <button type="button" className="boton-icono" onClick={salir} aria-label="Cerrar sesión" title="Cerrar sesión">
          <SignOut size={18} weight="bold" />
        </button>
      </div>
    </header>
  );
}
