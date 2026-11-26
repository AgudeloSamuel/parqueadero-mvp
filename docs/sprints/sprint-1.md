# Sprint 1 – MVP Parqueadero

| Dato | Valor |
|---|---|
| Fechas | Del domingo 22 al jueves 26 de noviembre de 2026 |
| Product Owner | Samuel Agudelo |
| Scrum Master | Tomás Martínez |
| Desarrollo | Isaac Gracia |
| Capacidad comprometida | 36 puntos (28 iniciales + 8 de la HU-13) |

## Objetivo del sprint

Tener funcionando el ciclo básico de un vehículo: iniciar sesión, registrar el ingreso por
placa, generar el cobro del día, pagarlo en efectivo y validar la salida con la barrera
simulada (escenarios 1 a 4 de la demostración).

## Sprint Planning 1 – domingo 22 de noviembre

- El Product Owner presentó las historias HU-01 a HU-06.
- El equipo las estimó con **Planning Poker** (captura: `planning-poker-sprint-1.png`).
- Se acordaron los contratos compartidos del dominio (`domain/puertos/`) entre Samuel e Isaac.
- Las historias se movieron de *Backlog* a *Sprint (por hacer)* en el tablero.

### Sprint backlog

| Historia | Nombre | Responsable | Puntos | Rama |
|---|---|---|---|---|
| HU-01 | Iniciar sesión con rol | Isaac Gracia | 3 | `feature/HU01-login-roles` |
| HU-02 | Registrar ingreso por placa | Isaac Gracia | 5 | `feature/HU02-ingreso-placa` |
| HU-03 | Clasificar el vehículo por su placa | Samuel Agudelo | 2 | `feature/HU03-clasificacion-vehiculo` |
| HU-04 | Generar el cobro del día | Samuel Agudelo | 8 | `feature/HU04-generacion-cobro` |
| HU-05 | Registrar pago en efectivo | Samuel Agudelo | 5 | `feature/HU05-pago-efectivo` |
| HU-06 | Salida con barrera simulada | Isaac Gracia | 5 | `feature/HU06-salida-barrera` |
| HU-13 | Leer la placa con la cámara del PC | Isaac Gracia y Tomás Martínez | 8 | `feature/HU13-lectura-camara` |

Además, Tomás Martínez tiene a cargo el frontend base, las pantallas de Inicio de sesión,
Carril de entrada, Caja y Carril de salida, los mockups (DOC-02) y el plan de trabajo.

### Cambios durante el sprint

- **23/11:** la docente pidió leer la placa con la cámara del PC. Se agregó la **HU-13** (8 puntos).
- **23/11:** se ajustaron las reglas del parqueadero real: cobro único por día, carro $3.850
  (o $1.800 si entra desde las 5:30 p. m.), moto $0, ingreso de 4:00 a. m. a 11:59 p. m.
  y salida las 24 horas. Se agregó la validación de horario al ingreso.
- **23/11:** se cambió el orden de revisores: Tomás revisa a Samuel, Samuel a Isaac e Isaac a Tomás.

## Dailies

### Lunes 23 de noviembre

| Integrante | Qué hice | Qué haré | Bloqueos |
|---|---|---|---|
| Samuel | Repositorio, tablero e historias; revisión del esqueleto | HU-03 y contratos; empezar HU-04 | Ninguno |
| Isaac | Esqueleto con Docker y HU-01 (PR #14) | HU-02 ingreso por placa | Ninguno |
| Tomás | Plan de trabajo en formato APA | Mockups de las 7 pantallas | Ninguno |

### Martes 24 de noviembre

| Integrante | Qué hice | Qué haré | Bloqueos |
|---|---|---|---|
| Samuel | HU-03 (PR #17) y HU-04 (PR #19) | HU-05 pago en efectivo | Ninguno |
| Isaac | HU-02 (PR #16) y validación de horario (PR #18) | HU-06 salida | Ninguno |
| Tomás | Mockups en Figma ajustados a las reglas nuevas | Frontend base e inicio de sesión | Ninguno |

### Miércoles 25 de noviembre

| Integrante | Qué hice | Qué haré | Bloqueos |
|---|---|---|---|
| Samuel | HU-05 (PR #20) | Endpoint para buscar el cobro por placa; revisar el Documento de Análisis | Ninguno |
| Isaac | HU-06 (PR #23) | HU-13 lectura con OCR | Ninguno |
| Tomás | Documento de Análisis; frontend base, Carril de entrada, Carril de salida y cámara (HU-13) | Pantalla de Caja; Review 1 | La Caja necesita el endpoint para buscar el cobro por placa |

## Sprint Review 1 – jueves 26 de noviembre

_Completar en la reunión._

| Historia | Escenario mostrado | Resultado (aceptada / rechazada) | Observaciones |
|---|---|---|---|
| HU-01 | | | |
| HU-02 | | | |
| HU-03 | | | |
| HU-04 | | | |
| HU-05 | | | |
| HU-06 | | | |
| HU-13 | | | |

Puntos completados: __ de 36. Gráfico burn up: `burnup-sprint-1.png`.

## Retrospectiva 1

- **Qué salió bien:**
- **Qué mejorar:**
- **Acción para el Sprint 2:**
