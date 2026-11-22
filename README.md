# parqueadero-mvp

## Ejecutar el esqueleto

Con Docker Desktop iniciado, ejecuta desde la raíz del repositorio:

```powershell
Copy-Item .env.example .env
```

Ejecuta la copia una sola vez. Abre `.env` y asigna una contraseña local a
`POSTGRES_PASSWORD`.

```powershell
docker compose up --build -d
docker compose ps
Invoke-RestMethod http://localhost:8000/health
docker compose exec backend python -m pytest -v
```

`GET /health` devuelve `{"status":"ok"}` cuando responde la API. La
documentación interactiva está en <http://localhost:8000/docs>. El estado de
PostgreSQL se ve en `docker compose ps` y los datos se conservan en un volumen.

Cuando se integre React con Vite y su `package-lock.json`, levanta también el
frontend en el puerto 5173 con `docker compose --profile frontend up --build -d`.
