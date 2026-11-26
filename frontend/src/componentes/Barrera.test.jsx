import { render, screen } from "@testing-library/react";
import Barrera, { estiloBarrera } from "./Barrera.jsx";

describe("barrera", () => {
  it("ABIERTA es verde, CERRADA y LLENO rojos, PENDIENTE ámbar", () => {
    expect(estiloBarrera("ABIERTA").clase).toBe("barrera-verde");
    expect(estiloBarrera("CERRADA").clase).toBe("barrera-roja");
    expect(estiloBarrera("LLENO").clase).toBe("barrera-roja");
    expect(estiloBarrera("PENDIENTE_VALIDACION").clase).toBe("barrera-ambar");
  });

  it("muestra el estado y siempre el motivo", () => {
    render(<Barrera estado="CERRADA" motivo="Parqueadero cerrado" />);
    expect(screen.getByRole("status").textContent).toContain("Barrera cerrada");
    expect(screen.getByRole("status").textContent).toContain("Parqueadero cerrado");
  });

  it("muestra los valores del motivo con punto de miles", () => {
    render(<Barrera estado="CERRADA" motivo="Pago pendiente: $3850" />);
    expect(screen.getByText("Pago pendiente: $3.850")).toBeTruthy();
  });
});
