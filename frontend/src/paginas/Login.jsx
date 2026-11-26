import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { WarningCircle } from "@phosphor-icons/react";
import { api } from "../api/cliente.js";
import { guardarSesion, obtenerSesion } from "../auth/sesion.js";
import { inicioDe } from "../auth/rutas.js";
import { IlustracionParqueadero } from "../componentes/Ilustraciones.jsx";
import { saludo } from "../formato.js";

// HU-01: inicio de sesión con usuario y contraseña. Según el rol, va a su pantalla.
export default function Login() {
  const navegar = useNavigate();
  const [usuario, setUsuario] = useState("");
  const [clave, setClave] = useState("");
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);

  const sesion = obtenerSesion();
  if (sesion) return <Navigate to={inicioDe(sesion.rol)} replace />;

  async function ingresar(evento) {
    evento.preventDefault();
    setError("");
    setCargando(true);
    try {
      const { access_token, rol } = await api.login(usuario.trim(), clave);
      guardarSesion({ token: access_token, rol, usuario: usuario.trim() });
      navegar(inicioDe(rol), { replace: true });
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }

  return (
    <div className="login">
      <aside className="login-arte">
        <span className="marca marca-grande">
          <span className="marca-signo" aria-hidden="true">P</span>
          Parqueadero
        </span>
        <IlustracionParqueadero />
        <p className="login-lema">Cada carro, en su puesto. Cada cobro, en orden.</p>
      </aside>
      <main className="login-zona">
        <form className="login-form" onSubmit={ingresar}>
          <h1>{saludo()}</h1>
          <p className="suave">Inicia sesión para empezar tu turno.</p>
          <label className="campo">
            Usuario
            <input value={usuario} onChange={(e) => setUsuario(e.target.value)} autoComplete="username" required autoFocus />
          </label>
          <label className="campo">
            Contraseña
            <input type="password" value={clave} onChange={(e) => setClave(e.target.value)} autoComplete="current-password" required />
          </label>
          {error && (
            <p className="aviso aviso-error" role="alert">
              <WarningCircle size={18} weight="fill" aria-hidden="true" />
              {error}
            </p>
          )}
          <button type="submit" className="boton boton-primario boton-ancho" disabled={cargando}>
            {cargando ? "Ingresando..." : "Ingresar"}
          </button>
        </form>
      </main>
    </div>
  );
}
