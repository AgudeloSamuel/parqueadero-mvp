# Frontend (React + Vite)

Con el backend corriendo, levanta también el frontend:

```powershell
docker compose --profile frontend up --build -d
```

Abre <http://localhost:5173> e inicia sesión con un usuario creado en HU-01.
El OPERADOR entra al carril de entrada y ve Caja, Carril de salida y
Validación manual. El ADMIN entra a Consultas y Administración.

Para trabajar sin Docker (necesitas Node.js 22):

```powershell
cd frontend
npm install
npm run dev      # http://localhost:5173
npm test         # pruebas con Vitest
```

La dirección de la API se cambia con `VITE_API_URL` (ver `frontend/.env.example`).
