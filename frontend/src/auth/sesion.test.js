import { cerrarSesion, guardarSesion, obtenerSesion } from "./sesion.js";

describe("sesión", () => {
  beforeEach(() => sessionStorage.clear());

  it("guarda y lee el token y el rol", () => {
    guardarSesion({ token: "abc", rol: "ADMIN", usuario: "admin" });
    expect(obtenerSesion()).toEqual({ token: "abc", rol: "ADMIN", usuario: "admin" });
  });

  it("cerrar sesión la borra", () => {
    guardarSesion({ token: "abc", rol: "ADMIN", usuario: "admin" });
    cerrarSesion();
    expect(obtenerSesion()).toBeNull();
  });

  it("ignora datos dañados", () => {
    sessionStorage.setItem("parqueadero.sesion", "{no es json");
    expect(obtenerSesion()).toBeNull();
  });
});
