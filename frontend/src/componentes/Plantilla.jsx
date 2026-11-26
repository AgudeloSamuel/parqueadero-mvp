import { Outlet } from "react-router-dom";
import Menu from "./Menu.jsx";

export default function Plantilla() {
  return (
    <>
      <Menu />
      <main className="contenido">
        <Outlet />
      </main>
    </>
  );
}
