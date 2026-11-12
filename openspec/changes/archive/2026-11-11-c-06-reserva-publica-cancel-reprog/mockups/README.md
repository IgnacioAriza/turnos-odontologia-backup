# Mockups — C-06 reserva pública, cancelación y reprogramación

Maquetas HTML/CSS estáticas para aprobar el diseño de las tres pantallas públicas de
C-06 **antes de implementar**. No son la aplicación: no llaman a la API, no envían
formularios y no cancelan ni reprograman nada.

- **Modo de proyecto**: `system-and-mockups` (política elegida por el usuario).
- **Design system**: revisión 1 — `design-system/README.md`, `Approval: approved (2026-11-10, by user)`.
- **Fuente de valores visuales**: `design-system/tokens.css`, `design-system/brand.js` y
  `design-system/assets/logo.svg`. No hay colores, tipografías, radios ni sombras
  codificados a mano.
- **Approval**: approved (2026-11-11, by user).

## Archivos

| Archivo | Ruta real | Estados |
|---|---|---|
| `home.html` | `/` | 4 + desktop 1440 |
| `reservar.html` | `/reservar` | 6 + desktop 1440 |
| `gestionar.html` | `/gestionar/:token` | 6 + desktop 1440 |

Cada archivo incluye el encabezado de revisión ("Mockup estático — C-06 · design
system rev. 1"), la leyenda "No es la app · maqueta para aprobación" y, al final, una
sección **Desktop 1440** con el estado principal en layout ancho.

### Estados por pantalla

**`home.html` (4)**

1. Búsqueda inicial (sin horarios pedidos todavía).
2. Horarios cargados con un slot seleccionado.
3. Día sin horarios, con sugerencia de día siguiente.
4. Error de API con acción "Reintentar".

**`reservar.html` (6)**

1. Formulario vacío con resumen del turno (práctica, día/hora, seña 30 %).
2. Teléfono inválido (`aria-invalid`, `aria-describedby`, envío bloqueado).
3. Envío en curso (spinner + `aria-busy`, campos bloqueados).
4. 201 con URL de pago.
5. 201 sin URL de pago: se avisa que falta la integración y **no** se simula un pago aprobado.
6. 409 por solape: horarios refrescados y datos del formulario conservados.

**`gestionar.html` (6)**

1. Turno vigente (detalle, seña, reprogramaciones restantes = 1, cancelar + reprogramar).
2. Token inválido (403, sin datos del turno y sin enlace a `/login`).
3. Turno `cancelado` (acciones eliminadas, sin promesa de reembolso).
4. Diálogo de cancelación tardía (pérdida de seña, foco en la acción segura, cierre con Escape).
5. Diálogo de 2.ª reprogramación (`requiere_nueva_sena`, seña nueva, nada creado hasta confirmar).
6. Selector de horario nuevo (excluye el horario actual, tomados deshabilitados y tachados).

## Cómo verlos

Se abren como archivo local, sin servidor y sin build:

1. Abrí el HTML directamente en el navegador (`file:///.../mockups/home.html`).
2. Para mobile, poné el viewport en **390 × 844** (DevTools → modo dispositivo).
3. Para desktop, abrí la sección **Desktop 1440** y usá **1440 × 900**.
4. Los archivos se enlazan entre sí (`home → reservar`, `reservar → gestionar`) para
   recorrer el flujo completo.

No hacen falta fuentes remotas ni conexión: el logo es local y el nombre de marca se
inyecta desde `design-system/brand.js`.

> La inspección visual automatizada queda para la etapa de verify (contra la
> implementación real). Estas maquetas se revisan abriendo los archivos.

## Datos de escenario

Fijos y consistentes entre pantallas, para que las tres se lean como un mismo caso:

| Dato | Valor |
|---|---|
| Práctica | Limpieza dental · 40 min |
| Arancel | $ 30.000 |
| Seña | 30 % = $ 9.000 |
| Turno vigente | Jueves 12/11 · 09:30 a 10:10 |
| Escenario de cancelación tardía | Martes 10/11 · 18:30 (dentro de las 12 h) |
| Paciente | Juana Pérez · 11 5555 1234 |
| Zona horaria | America/Argentina/Buenos_Aires |

El segundo escenario existe porque un turno del 12/11 no puede estar dentro de la
ventana de 12 horas al mismo tiempo.

## Decisiones de layout no obvias

- **Marco de teléfono con alto automático**: se adapta al ancho disponible (343 px en un
  viewport de 390) y nunca supera los 390 px, sin recortar a 844 px de alto. Así ningún
  estado queda escondido; la etiqueta de estado y la anotación van al costado.
- **Todo colapsa por debajo de 1100 px**: el tablero (teléfono + anotaciones), la sección
  Desktop (deja de tener dos columnas y el resumen sticky) y los diálogos pasan a una
  sola columna; las acciones en fila y el stepper horizontal se apilan a ≤860 px. A
  1440 px se mantienen las dos columnas y el contenido centrado a 1200 px.
- **Anotación lateral por estado** ("Contrato", "Pendientes (TBD)", "Accesibilidad"):
  el revisor ve qué exige el backend, qué falta definir y qué cubre la accesibilidad,
  sin abrir otro documento.
- **Un solo `h1` por página** (título del tablero). Los estados usan `h2`, el título de
  pantalla dentro del teléfono `h3` y los títulos de diálogo `h4`.
- **Desktop full-bleed con contenido a 1200 px**: el frame ocupa los 1440 px, pero el
  contenido respeta `--layout-max`, igual que la app. `reservar` y `gestionar` usan
  `minmax(0, 1fr) 400px`; `home` usa `380px minmax(0, 1fr)`.
- **Diálogos superpuestos con CSS Grid**: la página de fondo, el velo y el diálogo
  comparten la misma celda (`grid-area: 1 / 1`); el velo usa `--color-overlay` y el
  diálogo `--shadow-lg`. No hay JS de diálogo: es estático y semántico.
- **La acción destructiva nunca recibe el foco inicial**: en el diálogo de cancelación
  "Volver" es el botón primario y tiene el foco; "Cancelar y perder la seña" usa tokens
  de peligro. En el de seña nueva el foco también arranca en "Volver", aunque la acción
  de avance ("Aceptar y pagar seña nueva") sea la primaria.
- **El estado nunca depende del color**: badges con texto ("Confirmado", "Cancelado"),
  slots tomados con `disabled` + tachado, avisos con texto además del borde.
- **Sin "Iniciar sesión" en el header público**: esas pantallas no autentican pacientes
  y el enlace llevaría al flujo del personal. Ver TBD.

## Ambigüedades marcadas `(TBD)`

Están señaladas también dentro de cada HTML, junto al estado afectado. Ninguna se
resolvió inventando contrato o copy.

| # | Pantalla | Ambigüedad |
|---|---|---|
| 1 | home | `GET /api/public/slots` exige el UUID de la práctica, pero no hay endpoint público que liste prácticas: de dónde sale el selector queda sin definir. |
| 2 | home | La sugerencia de "día siguiente con horarios" no existe en la API: hoy requiere pedir día por día. |
| 3 | home / reservar | El contrato público no expone arancel ni `sena_pct` antes de reservar: la seña de $ 9.000 se conoce recién en la respuesta 201 (`monto_sena`). |
| 4 | reservar | `ReservaOut` no tiene campo de URL de pago: el enlace de Mercado Pago depende de C-08. |
| 5 | reservar | El 409 de `POST /api/public/reservas` no trae `codigo` estable (a diferencia de gestión, que usa `solape`): el cliente no puede distinguir el motivo sin mirar el texto. |
| 6 | reservar | No está definido qué hacer si el refresco de horarios falla mientras el 409 está en pantalla. |
| 7 | reservar / gestionar | `mp_ttl_min` (TTL del turno `pendiente_sena`) no tiene valor ni copy definidos para "tu turno expira en…". |
| 8 | gestionar | No existe ruta pública para pegar un código de gestión (`/gestionar` sin token): con un enlace roto solo queda contactar a la clínica o el reenvío de C-10. |
| 9 | gestionar | El aviso de 2.ª reprogramación llega después de elegir el horario, aunque `reprogramaciones_restantes` ya se conoce al abrir la vista. |
| 10 | gestionar | El turno nuevo de la 2.ª reprogramación tiene otro `manage_token`: no está definido si se redirige o se muestra el enlace para guardar. |
| 11 | gestionar | No hay copy ni flujo de reembolso en C-06 (se define en C-08); el mockup dice "retenida" y no promete devolución. |
| 12 | gestionar | La vista no expone la fecha de cancelación ni el nombre del paciente: el mockup no los muestra como dato real. |
| 13 | gestionar | `monto_sena` no distingue seña cobrada de pendiente: el texto de pérdida no debería aparecer en `pendiente_sena`. Regla de UI pendiente. |
| 14 | gestionar | El 409 `solape` al reprogramar no tiene copy definido para esta pantalla. |
| 15 | global | Copy específico de rate limit (`rate_limited`, 30/min por IP y 10/min por token) sin definir. |
| 16 | global | Política del header público: se omitió "Iniciar sesión" y no se enlaza "Gestionar mi turno" desde home. |

## Fuentes usadas

- `openspec/changes/c-06-reserva-publica-cancel-reprog/proposal.md`, `design.md`
  (D1–D10 y `## UI Mockups`), `specs/booking-publico/spec.md`, `specs/gestion-turnos/spec.md`.
- `backend/app/api/public/reservas.py`, `backend/app/api/public/gestion.py`.
- `backend/app/domain/turnos/schemas.py`, `gestion.py`, `service.py`.
- `backend/app/core/exceptions.py`.
- `design-system/README.md`, `brand.md`, `tokens.css`, `brand.js`, `components.html`.
- `frontend/src/pages/ManageAppointmentPage.tsx`, `frontend/src/layouts/PublicLayout.tsx`,
  `frontend/src/router.tsx` (estado actual de los stubs).

Los textos de error son los reales del backend, por ejemplo
`"El enlace de gestión no es válido"` (403, `token_invalido`),
`"Cancelar dentro de las 12 horas hace perder la seña"` (`requiere_confirmacion`),
`"La segunda reprogramación exige una seña nueva"` (`requiere_nueva_sena`) y
`"El horario seleccionado ya no está disponible"` (409 de solape).

## Fuera de alcance

- No se tocó backend, `frontend/src`, `design-system/` ni `design.md`.
- Las capturas de `previews/` (390 y 1440) se tomaron antes del ajuste responsive:
  hay que regenerarlas para revisar la versión corregida.
- No se maqueta el flujo de pago de Mercado Pago (C-08) ni el recordatorio de WhatsApp (C-10).
- No se maqueta el 404 de gestión ni el reenvío de enlace.

## Aprobación

`Approval: approved (2026-11-11, by user)`

Para aprobar: revisar los tres HTML en 390 px y las secciones Desktop 1440, y confirmar
explícitamente la revisión. Cualquier cambio de contenido o de token vuelve la
aprobación a `pending` y obliga a revisar los estados afectados.

