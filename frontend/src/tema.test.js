import { aplicarTema, temaEfectivo, temaGuardado } from "./tema.js";

describe("tema claro u oscuro", () => {
  beforeEach(() => {
    localStorage.clear();
    delete document.documentElement.dataset.tema;
    window.matchMedia = vi.fn(() => ({ matches: false }));
  });

  it("sin preferencia guardada sigue al sistema", () => {
    expect(temaGuardado()).toBeNull();
    expect(temaEfectivo()).toBe("claro");
    window.matchMedia = vi.fn(() => ({ matches: true }));
    expect(temaEfectivo()).toBe("oscuro");
  });

  it("recuerda el tema que elige el operador", () => {
    aplicarTema("oscuro");
    expect(document.documentElement.dataset.tema).toBe("oscuro");
    expect(temaEfectivo()).toBe("oscuro");
  });
});
