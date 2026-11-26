import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import Camara from "./Camara.jsx";

describe("cámara del PC (HU-13)", () => {
  let detener;
  beforeEach(() => {
    detener = vi.fn();
    navigator.mediaDevices = { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop: detener }] }) };
    HTMLMediaElement.prototype.play = vi.fn().mockResolvedValue();
    HTMLCanvasElement.prototype.getContext = vi.fn(() => ({ drawImage: vi.fn() }));
    HTMLCanvasElement.prototype.toBlob = function (listo) {
      listo(new Blob(["foto"], { type: "image/jpeg" }));
    };
  });

  it("enciende la cámara y entrega la foto como placa.jpg", async () => {
    const onCaptura = vi.fn();
    render(<Camara onCaptura={onCaptura} />);
    fireEvent.click(screen.getByRole("button", { name: "Encender cámara" }));
    fireEvent.click(await screen.findByRole("button", { name: "Capturar placa" }));
    expect(onCaptura).toHaveBeenCalledTimes(1);
    const archivo = onCaptura.mock.calls[0][0];
    expect(archivo.name).toBe("placa.jpg");
    expect(archivo.type).toBe("image/jpeg");
  });

  it("al apagarla detiene la cámara", async () => {
    render(<Camara onCaptura={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Encender cámara" }));
    fireEvent.click(await screen.findByRole("button", { name: "Apagar cámara" }));
    expect(detener).toHaveBeenCalled();
    expect(screen.getByText("Cámara apagada")).toBeTruthy();
  });

  it("sin permiso muestra un mensaje claro", async () => {
    navigator.mediaDevices.getUserMedia.mockRejectedValue(Object.assign(new Error(), { name: "NotAllowedError" }));
    render(<Camara onCaptura={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Encender cámara" }));
    await waitFor(() => expect(screen.getByText(/No diste permiso para usar la cámara/)).toBeTruthy());
  });
});
