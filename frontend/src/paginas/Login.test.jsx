import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import Login from "./Login.jsx";
import { obtenerSesion } from "../auth/sesion.js";

function montar() {
  render(
    <MemoryRouter initialEntries={["/login"]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/entrada" element={<p>Pantalla del operador</p>} />
      </Routes>
    </MemoryRouter>,
  );
  fireEvent.change(screen.getByLabelText("Usuario"), { target: { value: "operador" } });
  fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: "clave" } });
  fireEvent.click(screen.getByRole("button", { name: "Ingresar" }));
}

describe("HU-01 inicio de sesión", () => {
  beforeEach(() => {
    sessionStorage.clear();
    globalThis.fetch = vi.fn();
  });

  it("con credenciales correctas guarda la sesión y va a la pantalla del rol", async () => {
    fetch.mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve({ access_token: "jwt", rol: "OPERADOR" }) });
    montar();
    expect(await screen.findByText("Pantalla del operador")).toBeTruthy();
    expect(obtenerSesion()).toEqual({ token: "jwt", rol: "OPERADOR", usuario: "operador" });
  });

  it("con credenciales incorrectas muestra el error y no guarda sesión", async () => {
    fetch.mockResolvedValue({ ok: false, status: 401, json: () => Promise.resolve({ detail: "Usuario o contraseña incorrectos" }) });
    montar();
    expect(await screen.findByText("Usuario o contraseña incorrectos")).toBeTruthy();
    expect(obtenerSesion()).toBeNull();
  });
});
