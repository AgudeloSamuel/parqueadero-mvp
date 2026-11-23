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

## HU-01. Iniciar sesión

Agrega una clave aleatoria propia de al menos 32 bytes en `JWT_SECRET` en tu
`.env`. Levanta los servicios y aplica la migración para crear la tabla
`usuarios`, incluso si ya tenías un volumen de PostgreSQL del esqueleto.
Las tablas de cada historia se crean con migraciones de Alembic. El script
`db/init.sql` se ejecuta solo al inicializar un volumen vacío.

Por defecto, el backend se conecta al servicio `db` con los valores
`POSTGRES_*` de `.env`. Para indicar otra conexión, configura `DATABASE_URL`
en el mismo archivo con el formato
`postgresql+psycopg2://usuario:clave@host:5432/base`. Usa `db` como host
si la base está en el mismo Compose y codifica los caracteres reservados de
la contraseña en la URL, por ejemplo `@` como `%40`.

```powershell
docker compose up --build -d
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.infrastructure.crear_usuario admin ADMIN
docker compose exec backend python -m app.infrastructure.crear_usuario operador OPERADOR
```

Cada comando de creación solicita la contraseña sin mostrarla y guarda su hash
bcrypt. Desde <http://localhost:8000/docs> se puede llamar a
`POST /api/v1/auth/login` con el JSON `{"username":"admin","password":"..."}`.
La respuesta entrega `access_token` y `rol`. El cliente React usa `rol` para
navegar a la pantalla correspondiente y envía `Authorization: Bearer <token>`
en las solicitudes protegidas.

`GET /api/v1/admin/acceso` y `GET /api/v1/consultas/acceso` permiten comprobar
el acceso de ADMIN. La ruta `GET /api/v1/admin/tarifas` comprueba el permiso
desde HU-01 y responde 501 para ADMIN hasta que HU-09 implemente tarifas.

## HU-02. Registrar ingreso por placa

Levanta el backend y aplica la migración que crea la tabla `eventos`.
Usa `-p parqueadero-hu01` después de `docker compose` en todos los comandos
si tu base de HU-01 está en ese proyecto de Compose.

```powershell
docker compose up --build -d
docker compose exec backend alembic upgrade head
docker compose exec backend python -m pytest -v --color=yes
```

Si todavía no existe un operador, créalo con
`docker compose exec backend python -m app.infrastructure.crear_usuario operador OPERADOR`.
En <http://localhost:8000/docs> ejecuta `POST /api/v1/auth/login` con ese usuario,
copia el `access_token` y pégalo en **Authorize**.

| Escenario | Solicitud | Resultado |
|---|---|---|
| Entrada válida | En `POST /api/v1/carril/entrada`, envía `{"placa":"ABC123","confianza":0.95,"sede_id":1}` | `201`, evento `ENTRADA` y barrera `ABIERTA`. |
| Normalización | Envía `{"placa":" abc-123 ","confianza":0.95,"sede_id":1}` | Se guarda `ABC123`. |
| Placa inválida | Envía `{"placa":"AB-12","confianza":0.95,"sede_id":1}` | `422` con `Formato de placa inválido`, sin guardar un evento. |
| Fuera de rango | Envía la lectura válida con `confianza: 1.1` | `422`, sin guardar un evento. |
| Lectura de imagen | En `POST /api/v1/carril/entrada/imagen`, sube un PNG o JPEG recortado a la placa y completa `sede_id`. | Tesseract extrae la placa y su confianza entre 0 y 1. |

Para ver la **barrera verde**, abre <http://localhost:8000/demo/carril>,
pega el token de operador y registra la lectura precargada. Esta vista también
acepta una imagen. Con confianza inferior a `UMBRAL_CONFIANZA` (0.80 por defecto)
la lectura queda en `PENDIENTE_VALIDACION` y la barrera permanece cerrada.
HU-04 conectará el cobro real.

Para comprobar qué quedó guardado en PostgreSQL, sustituye `parqueadero` por
el usuario y la base de tu `.env` cuando sean distintos:

```powershell
docker compose exec db psql -U parqueadero -d parqueadero -c 'SELECT id, tipo, placa, fecha_hora, sede_id, confianza, barrera FROM eventos ORDER BY id;'
```
