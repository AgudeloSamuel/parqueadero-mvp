import { mensajeDeError, pedir } from "./cliente.js";
import { guardarSesion, obtenerSesion } from "../auth/sesion.js";

function respuesta(status, cuerpo) {
  return Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(cuerpo) });
}

describe("cliente HTTP", () => {
  beforeEach(() => {
    sessionStorage.clear();
    globalThis.fetch = vi.fn();
  });

  it("envía el token en Authorization", async () => {
    guardarSesion({ token: "t123", rol: "OPERADOR", usuario: "op" });
    fetch.mockReturnValue(respuesta(200, { ok: true }));
    await pedir("/algo");
    expect(fetch.mock.calls[0][1].headers.Authorization).toBe("Bearer t123");
  });

  it("con 401 cierra la sesión y lanza el mensaje del backend", async () => {
    guardarSesion({ token: "vencido", rol: "OPERADOR", usuario: "op" });
    fetch.mockReturnValue(respuesta(401, { detail: "Token ausente, inválido o vencido" }));
    await expect(pedir("/algo")).rejects.toThrow("Token ausente, inválido o vencido");
    expect(obtenerSesion()).toBeNull();
  });

  it("si el backend no responde, da un mensaje claro", async () => {
    fetch.mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(pedir("/algo")).rejects.toThrow("No hay conexión con el servidor");
  });

  it("convierte los errores 422 de FastAPI en texto", () => {
    expect(mensajeDeError({ detail: [{ msg: "Campo requerido" }] }, 422)).toBe("Campo requerido");
  });
});
