import { fireEvent, render, screen } from "@testing-library/react";
import CarrilSalida from "./CarrilSalida.jsx";
import { guardarSesion } from "../auth/sesion.js";

function responde(status, cuerpo) {
  fetch.mockResolvedValue({ ok: status < 400, status, json: () => Promise.resolve(cuerpo) });
}

function validar(placa) {
  render(<CarrilSalida />);
  fireEvent.change(screen.getByLabelText("Placa"), { target: { value: placa } });
  fireEvent.click(screen.getByRole("button", { name: "Validar salida" }));
}

const base = { evento_id: 1, sede_id: 1, fecha_hora: "2026-11-25T10:49:00-05:00", tipo_vehiculo: "CARRO" };

describe("pantalla Carril de salida (HU-06)", () => {
  beforeEach(() => {
    sessionStorage.clear();
    guardarSesion({ token: "jwt", rol: "OPERADOR", usuario: "operador" });
    globalThis.fetch = vi.fn();
  });

  it("con el pago verificado muestra la barrera abierta", async () => {
    responde(201, { ...base, placa: "ABC123", barrera: "ABIERTA", motivo: "Pago verificado" });
    validar("ABC123");
    expect(await screen.findByText("Barrera abierta")).toBeTruthy();
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ placa: "ABC123", sede_id: 1 });
  });

  it("con pago pendiente muestra la barrera cerrada y manda a la caja", async () => {
    responde(201, { ...base, placa: "KLM321", barrera: "CERRADA", motivo: "Pago pendiente: $3850" });
    validar("KLM321");
    expect(await screen.findByText("Barrera cerrada")).toBeTruthy();
    expect(screen.getByText("El conductor debe pasar por la caja.")).toBeTruthy();
  });

  it("con placa inválida muestra el error", async () => {
    responde(422, { detail: "Formato de placa inválido" });
    validar("12");
    expect(await screen.findByText("Formato de placa inválido")).toBeTruthy();
  });
});
