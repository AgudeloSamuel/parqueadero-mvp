import { inicioDe, pantallasDe } from "./rutas.js";

describe("rutas por rol (F-10)", () => {
  it("el operador no ve Administración ni Consultas", () => {
    const nombres = pantallasDe("OPERADOR").map((p) => p.nombre);
    expect(nombres).toEqual(["Carril de entrada", "Caja", "Carril de salida", "Validación manual"]);
  });

  it("cada rol empieza en su primera pantalla", () => {
    expect(inicioDe("OPERADOR")).toBe("/entrada");
    expect(inicioDe("ADMIN")).toBe("/consultas");
  });

  it("un rol desconocido vuelve al login", () => {
    expect(inicioDe("OTRO")).toBe("/login");
  });
});
