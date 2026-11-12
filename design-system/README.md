# Sistema de diseño — Turnos Odontología

Mode: system-and-mockups
Revision: 1
Approval: approved (2026-11-10, by user)
Decided: 2026-11-10 (usuario, vía `/active-orchestrator:design`)
Owner: `design-system` (skill) · consumido por `design-mockups` en cada change con UI

---

## Qué es esto

La fundación visual **portable** del proyecto: tokens, marca y componentes de
referencia en HTML/CSS plano. No depende de Figma, de fuentes remotas, de cuentas
pagas ni de un agente específico. Cualquier agente (Claude, Codex, OpenCode,
Antigravity) lee los mismos archivos y produce mockups comparables.

Con la política `system-and-mockups`, este sistema se aprueba **una vez** y luego
cada change con interfaz debe mostrar un mockup HTML propio para revisión antes
de implementar.

## Archivos

| Archivo | Rol | Reemplazable sin tocar mockups |
|---|---|---|
| `tokens.css` | Colores, tipografía, espaciado, radios, sombras, foco, movimiento, dark mode y `prefers-reduced-motion` | Sí — cambiando el valor del token |
| `brand.md` | Voz, tono, reglas de logo, imágenes, color y accesibilidad | Sí |
| `brand.js` | `BRAND_NAME` único + binding de `[data-brand-name]` y `<html data-brand-title>` | Sí — una constante |
| `assets/logo.svg` | Ruta estable del logo (hoy **placeholder rotulado**) | Sí — sobrescribir el archivo |
| `components.html` | Referencia viva de componentes y estados | No aplica |
| `previews/` | Capturas mobile y desktop de `components.html` | Regenerables |

## Fuente de los valores

Los tokens **no se inventaron**: se derivaron de la identidad ya existente del
frontend, para no rebrandear de prepo.

- `frontend/src/index.css` — paleta, tipografía, espaciado, radios, sombras, dark
  mode, `--touch-target: 44px`.
- `frontend/src/pages/HomePage.css` — gradiente del hero (`#eff6ff → #dbeafe`) y
  azul profundo de titulares (`#1e3a8a`).
- `frontend/src/pages/ManageAppointmentPage.css` — altura de control 48 px y anillo
  de foco `rgba(37, 99, 235, 0.25)`.
- `frontend/src/layouts/PublicLayout.css` — header, brand y estados de navegación.
- `frontend/index.html` — nombre de producto, `lang="es-AR"`, `theme-color`.

Adiciones (no cambian ningún valor existente): superficies de estado
(`--color-success-light`, etc.), `--color-border-strong`, `--layout-*`,
`--gradient-hero`, `--easing-standard`, `--shadow-focus`.

> **Regla de sincronización**: `tokens.css` es la referencia portable; la
> implementación vive en `frontend/src/index.css`. Al crear o cambiar un token acá,
> reflejá el mismo valor en el CSS del frontend en el mismo change. Si divergen, la
> referencia es este archivo y el frontend es el bug.

## Decisiones abiertas `(TBD)`

Todas están aisladas para poder aprobar el sistema igual y resolverlas después.

1. **Nombre comercial de la clínica** — hoy el producto se llama
   "Turnos Odontología" (título del `index.html`). Reemplazo: `BRAND_NAME` en
   `brand.js` + recompilar previews.
2. **Logo definitivo** — `assets/logo.svg` es un placeholder con la leyenda
   "LOGO PROVISORIO" y un diente en azul de marca. Reemplazo: sobrescribir el
   archivo, mismo `viewBox` o proporción similar (260×72 recomendado).
3. **Favicon** — `frontend/public/favicon.svg` es un asset violeta `#863bff` ajeno
   a la marca. Debe reemplazarse por el logo definitivo.
4. **Logo para fondo oscuro / monocromo** — no existe. `(TBD)`.
5. **Fotografía de clínica y profesionales** — no hay assets del cliente. `(TBD)`.
6. **Modo oscuro de las superficies de estado** — definidas por criterio de
   contraste, sin validación visual real en dispositivo. `(TBD)` revisar en device.

## Cómo previsualizar

Abrir `design-system/components.html` en cualquier navegador (doble clic o
`file://`). Los estilos cargan desde `tokens.css` y el nombre desde `brand.js`,
así que conviene abrirlo desde la carpeta, no copiarlo suelto.

- Mobile: 390 × 844.
- Desktop: 1440 × 900.
- Capturas de referencia: `design-system/previews/`.

## Cómo cambiar el sistema

1. Editá el token o el asset (nunca un valor hardcodeado en un mockup).
2. Subí `Revision:` en este archivo y poné `Approval: pending`.
3. Actualizá `visual_design.status` a `pending` en `.active-orchestrator-state.json`.
4. Regenerá las capturas de `previews/`.
5. Identificá qué mockups aprobados usan el token cambiado y pedí revisión de
   nuevo solo en esos.

## Gate de mockups por change

En cada change con UI, antes de implementar:

1. `openspec/changes/<change>/mockups/` con HTML responsive por pantalla y estado.
2. Importar `../../design-system/tokens.css` y `../../design-system/brand.js`.
   (Ruta relativa desde el change; si no resuelve, servir el repo desde la raíz.)
3. Capturas 390×844 y 1440×900 en `mockups/previews/`.
4. Aprobación explícita del usuario; recién ahí `Approval: approved (<fecha>, by user)`
   en el `README` del change y `Approval: approved (<fecha>, by user)` acá si cambió
   la revisión del sistema.

Nunca se modifica silenciosamente un mockup ya aprobado.
