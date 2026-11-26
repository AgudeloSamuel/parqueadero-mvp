import { fireEvent, render, screen } from "@testing-library/react";
import CarrilEntrada from "./CarrilEntrada.jsx";
import { guardarSesion } from "../auth/sesion.js";

function responde(status, cuerpo) {
  fetch.mockResolvedValue({ ok: status < 400, status, json: () => Promise.resolve(cuerpo) });
}

function registrar(placa) {
  render(<CarrilEntrada />);
  fireEvent.click(screen.getByRole("tab", { name: "Manual" }));
  fireEvent.change(screen.getByLabelText("Placa"), { target: { value: placa } });
  fireEvent.click(screen.getByRole("button", { name: "Registrar ingreso" }));
}

describe("pantalla Carril de entrada", () => {
  beforeEach(() => {
    sessionStorage.clear();
    guardarSesion({ token: "jwt", rol: "OPERADOR", usuario: "operador" });
    globalThis.fetch = vi.fn();
  });

  it("envía la lectura y muestra la barrera abierta con el cobro", async () => {
    responde(201, {
      evento_id: 1, placa: "ABC123", confianza: 0.95, sede_id: 1,
      fecha_hora: "2026-11-25T10:45:00-05:00", tipo_vehiculo: "CARRO",
      barrera: "ABIERTA", motivo: "Ingreso registrado", cobro: { id: 7, valor: 3850, estado: "PENDIENTE" },
    });
    registrar("ABC123");
    expect(await screen.findByText("Barrera abierta")).toBeTruthy();
    expect(screen.getByText("$3.850 (pendiente)")).toBeTruthy();
    expect(screen.getByLabelText("Placa ABC123")).toBeTruthy();
    const cuerpo = JSON.parse(fetch.mock.calls[0][1].body);
    expect(cuerpo).toEqual({ placa: "ABC123", confianza: 0.95, sede_id: 1 });
  });

  it("con placa inválida muestra el error del backend", async () => {
    responde(422, { detail: "Formato de placa inválido" });
    registrar("AB-12");
    expect(await screen.findByText("Formato de placa inválido")).toBeTruthy();
    expect(screen.queryByRole("status")).toBeNull();
  });
});

