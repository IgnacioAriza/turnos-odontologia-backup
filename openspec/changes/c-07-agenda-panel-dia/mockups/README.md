# Mockups — C-07 agenda multi-sillón y panel del día

- Change: `c-07-agenda-panel-dia`
- Design system: revisión 1 (`design-system/README.md`, aprobada 2026-11-10 por el usuario)
- Política: `system-and-mockups`
- Fecha de creación: 2026-11-12
- **Approval: approved (2026-11-12, by user)**

## Pantallas

| Archivo | Ruta real | Rol | Estados incluidos |
|---|---|---|---|
| `agenda.html` | `/agenda` | recepción / admin | día multi-sillón, semana, filtros activos, día vacío, alta de turno con `solape · 409`, paciente bloqueado con `bloqueado · 403` y motivo auditado, variante de navegación del odontólogo |
| `panel-dia.html` | `/panel` | recepción / admin | resumen de la jornada, lista por hora con seña y WhatsApp, turno pendiente sin acciones de marcado, confirmación de ausencia con aviso de 2.ª falta, resultados (`completado`, bloqueo automático, `estado_no_actualizable · 409`, `turno_no_encontrado · 404`), día vacío |
| `odonto.html` | `/agenda` (rol `odonto`) | odontólogo | solo sus turnos, marcado de llegada/ausencia propia, límites (`404` turno ajeno, `409` estado no actualizable), día sin turnos propios |

`mockups.css` contiene solo layout y componentes de estas pantallas. Los valores
visuales se consumen de `design-system/tokens.css`; el nombre de la marca, de
`design-system/brand.js`; el logo, de `design-system/assets/logo.svg`.

## Datos y contratos usados

- Fecha de ejemplo: jueves 12/11/2026, zona `America/Argentina/Buenos_Aires`.
- Turnos: 3 sillones, 2 odontólogos (`dra.gomez@clinica.com`, `dr.perez@clinica.com`).
- Estados de turno: `pendiente_sena`, `confirmado`, `completado`, `ausente`.
- `estado_sena` derivado: `pendiente`, `aprobada`, `perdida`, `no_requerida`.
- Códigos reales del backend: `solape`, `bloqueado`, `motivo_requerido`,
  `estado_no_actualizable`, `turno_no_encontrado`.
- El panel es la única pantalla que muestra el teléfono del paciente; la agenda no.
- El alta interna y el marcado usan el motor y las reglas de C-05/C-07; el
  frontend no reimplementa solapes ni bloqueos.

## Cómo previsualizar

Desde la raíz del repo:

```powershell
python -m http.server 5500
```

Y abrir:

- http://localhost:5500/openspec/changes/c-07-agenda-panel-dia/mockups/agenda.html
- http://localhost:5500/openspec/changes/c-07-agenda-panel-dia/mockups/panel-dia.html
- http://localhost:5500/openspec/changes/c-07-agenda-panel-dia/mockups/odonto.html

También se pueden abrir con doble clic (`file://`): las rutas relativas a
`design-system/` resuelven desde la carpeta del change.

Viewports de revisión:

- Mobile: 390 × 844.
- Desktop: 1440 × 900.

Capturas: `mockups/previews/` (renderizadas 2026-11-12 con Chrome headless, ancho exacto y alto completo).

| Pantalla | Mobile 390 | Desktop 1440 |
|---|---|---|
| Agenda | `previews/agenda-390.png` (390×6498) | `previews/agenda-1440.png` (1440×3500) |
| Panel del día | `previews/panel-dia-390.png` (390×4415) | `previews/panel-dia-1440.png` (1440×2436) |
| Odontólogo | `previews/odonto-390.png` (390×2649) | `previews/odonto-1440.png` (1440×1694) |

## Comportamiento responsive

- **Día**: grilla hora × sillón en desktop; en ≤720 px cada hora es un bloque y
  cada turno muestra `hora · sillón` dentro de la tarjeta.
- **Semana**: 7 columnas en desktop, 4 en tablet y lista apilada por día en mobile.
- **Panel**: tabla en desktop; en mobile la fila se reordena a paciente/estado,
  práctica/seña y acciones, sin scroll horizontal.
- **Odontólogo**: misma lista responsive; sin acciones de alta, cancelación ni
  reprogramación.

## Verificación contra la implementación

`verify/` contiene las capturas de la app real (no de los mockups) tomadas el
2026-11-13 con Chrome headless por CDP, autenticadas con los tres roles:

| Grupo | Archivos | Viewports |
|:--|:--|:--|
| Páginas | `agenda-recepcion-*`, `panel-recepcion-*`, `agenda-odonto-*`, `agenda-semana-recepcion-*` | 390×844 y 1440×900 |
| Diálogos | `dialogo-alta-*`, `dialogo-excepcion-*`, `dialogo-ausencia-*` | 390×844 y 1440×900 |

Cada grupo tiene variante `-dark` (`prefers-color-scheme: dark`). El resumen con
overflow, errores de consola/red, contraste por selector y las diferencias
encontradas está en `verify/resumen.md`; los informes crudos, en
`verify/informe-{light,dark}.json` y `verify/informe-dialogos-{light,dark}.json`.

## Aprobación

Aprobado el **2026-11-12** por el usuario, registrado en este archivo y en
`design.md` §UI Mockups. Cualquier cambio visual posterior resetea la aprobación
a `pending` y se vuelve a presentar antes de tocar la implementación.
