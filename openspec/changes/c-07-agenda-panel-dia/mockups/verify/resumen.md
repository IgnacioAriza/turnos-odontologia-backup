# Verificación visual de C-07 — resumen automático

Capturas generadas por CDP contra la implementación real (`/agenda` y `/panel`),
con datos sembrados del 2026-11-13 y tokens del design system revisión 1.

## Páginas — esquema light

| Captura | Overflow | Alto | Errores |
|---|---|---|---|
| `agenda-recepcion-390.png` | 0 px | 1904 px | ninguno |
| `agenda-recepcion-1440.png` | 0 px | 1500 px | ninguno |
| `panel-recepcion-390.png` | 0 px | 2539 px | ninguno |
| `panel-recepcion-1440.png` | 0 px | 1438 px | ninguno |
| `agenda-odonto-390.png` | 0 px | 1537 px | ninguno |
| `agenda-odonto-1440.png` | 0 px | 931 px | ninguno |
| `agenda-semana-recepcion-390.png` | 0 px | 1898 px | ninguno |
| `agenda-semana-recepcion-1440.png` | 0 px | 1334 px | ninguno |

| Selector | Contraste | AA (4.5) |
|---|---|---|
| `.page-header h1` | 14.68:1 | sí |
| `.page-subtitle` | 7.56:1 | sí |
| `.agenda-turno strong` | 12.56:1 | sí |
| `.agenda-turno__meta` | 6.47:1 | sí |
| `.agenda-badge` | 11.46:1 | sí |
| `.panel-paciente strong` | 14.68:1 | sí |
| `.panel-meta` | 7.56:1 | sí |
| `.panel-badge` | 11.46:1 | sí |
| `.panel-resumen` | 7.23:1 | sí |

Objetivos táctiles < 44 px: Panel, Turnos Odontología. Son el logotipo y el enlace «Panel» de la barra superior: superan 24×24 px (mínimo AA de WCAG 2.2, 2.5.8), pero no llegan al 44×44 recomendado (AAA).

## Páginas — esquema dark

| Captura | Overflow | Alto | Errores |
|---|---|---|---|
| `agenda-recepcion-390-dark.png` | 0 px | 1904 px | ninguno |
| `agenda-recepcion-1440-dark.png` | 0 px | 1500 px | ninguno |
| `panel-recepcion-390-dark.png` | 0 px | 2539 px | ninguno |
| `panel-recepcion-1440-dark.png` | 0 px | 1438 px | ninguno |
| `agenda-odonto-390-dark.png` | 0 px | 1537 px | ninguno |
| `agenda-odonto-1440-dark.png` | 0 px | 931 px | ninguno |
| `agenda-semana-recepcion-390-dark.png` | 0 px | 1898 px | ninguno |
| `agenda-semana-recepcion-1440-dark.png` | 0 px | 1334 px | ninguno |

| Selector | Contraste | AA (4.5) |
|---|---|---|
| `.page-header h1` | 16.98:1 | sí |
| `.page-subtitle` | 12.04:1 | sí |
| `.agenda-turno strong` | 14.22:1 | sí |
| `.agenda-turno__meta` | 10.08:1 | sí |
| `.agenda-badge` | 12.52:1 | sí |
| `.panel-paciente strong` | 16.98:1 | sí |
| `.panel-meta` | 12.04:1 | sí |
| `.panel-badge` | 12.52:1 | sí |
| `.panel-resumen` | 9.96:1 | sí |

Objetivos táctiles < 44 px: Panel, Turnos Odontología. Son el logotipo y el enlace «Panel» de la barra superior: superan 24×24 px (mínimo AA de WCAG 2.2, 2.5.8), pero no llegan al 44×44 recomendado (AAA).

## Diálogos — esquema light

| Captura | Overflow | Alto | Errores |
|---|---|---|---|
| `dialogo-alta-390.png` | 0 px | 1904 px | ninguno |
| `dialogo-alta-1440.png` | 0 px | 1500 px | ninguno |
| `dialogo-excepcion-390.png` | 0 px | 1904 px | esperado: 403 bloqueado (abre la excepción) |
| `dialogo-excepcion-1440.png` | 0 px | 1500 px | esperado: 403 bloqueado (abre la excepción) |
| `dialogo-ausencia-390.png` | 0 px | 2539 px | ninguno |
| `dialogo-ausencia-1440.png` | 0 px | 1438 px | ninguno |

| Selector | Contraste | AA (4.5) |
|---|---|---|
| `.page-header h1` | 14.68:1 | sí |
| `.page-subtitle` | 7.56:1 | sí |
| `.agenda-turno strong` | 12.56:1 | sí |
| `.agenda-turno__meta` | 6.47:1 | sí |
| `.agenda-badge` | 11.46:1 | sí |
| `.agenda-dialog h3` | 14.68:1 | sí |
| `.agenda-elegido` | 10.36:1 | sí |
| `.agenda-resultado--elegido` | 13.49:1 | sí |
| `.agenda-dialog .agenda-alerta strong` | 5.91:1 | sí |
| `.agenda-dialog .agenda-alerta p` | 5.91:1 | sí |
| `.panel-paciente strong` | 14.68:1 | sí |
| `.panel-meta` | 7.56:1 | sí |
| `.panel-badge` | 11.46:1 | sí |
| `.panel-resumen` | 7.23:1 | sí |
| `.panel-dialog h3` | 14.68:1 | sí |
| `.panel-alerta--warning` | 4.84:1 | sí |

Objetivos táctiles < 44 px: Panel, Turnos Odontología. Son el logotipo y el enlace «Panel» de la barra superior: superan 24×24 px (mínimo AA de WCAG 2.2, 2.5.8), pero no llegan al 44×44 recomendado (AAA).

## Diálogos — esquema dark

| Captura | Overflow | Alto | Errores |
|---|---|---|---|
| `dialogo-alta-390-dark.png` | 0 px | 1904 px | ninguno |
| `dialogo-alta-1440-dark.png` | 0 px | 1500 px | ninguno |
| `dialogo-excepcion-390-dark.png` | 0 px | 1904 px | esperado: 403 bloqueado (abre la excepción) |
| `dialogo-excepcion-1440-dark.png` | 0 px | 1500 px | esperado: 403 bloqueado (abre la excepción) |
| `dialogo-ausencia-390-dark.png` | 0 px | 2539 px | ninguno |
| `dialogo-ausencia-1440-dark.png` | 0 px | 1438 px | ninguno |

| Selector | Contraste | AA (4.5) |
|---|---|---|
| `.page-header h1` | 16.98:1 | sí |
| `.page-subtitle` | 12.04:1 | sí |
| `.agenda-turno strong` | 14.22:1 | sí |
| `.agenda-turno__meta` | 10.08:1 | sí |
| `.agenda-badge` | 12.52:1 | sí |
| `.agenda-dialog h3` | 16.98:1 | sí |
| `.agenda-elegido` | 12.48:1 | sí |
| `.agenda-resultado--elegido` | 14.0:1 | sí |
| `.agenda-dialog .agenda-alerta strong` | 6.62:1 | sí |
| `.agenda-dialog .agenda-alerta p` | 6.62:1 | sí |
| `.panel-paciente strong` | 16.98:1 | sí |
| `.panel-meta` | 12.04:1 | sí |
| `.panel-badge` | 12.52:1 | sí |
| `.panel-resumen` | 9.96:1 | sí |
| `.panel-dialog h3` | 16.98:1 | sí |
| `.panel-alerta--warning` | 10.09:1 | sí |

Objetivos táctiles < 44 px: Panel, Turnos Odontología. Son el logotipo y el enlace «Panel» de la barra superior: superan 24×24 px (mínimo AA de WCAG 2.2, 2.5.8), pero no llegan al 44×44 recomendado (AAA).

## Diferencias detectadas y resueltas

| Prioridad | Pantalla | Diferencia | Resolución |
|---|---|---|---|
| blocker | Agenda (≤720 px) | Matriz día con scroll horizontal y celdas recortadas | Se apila por hora: cabecera oculta y celdas a ancho completo |
| major | Agenda / Panel (oscuro) | `h1` heredaba un color oscuro sobre fondo oscuro | `.page-header` pasó a `index.css` y las reglas de `AdminPage.css` se scopearon a `.admin-page` |
| major | Agenda / Panel (oscuro) | Superficies de estado claras fijas | Tokens de estado (`--color-*-light/text`) con variante oscura en `index.css`, igual que el design system |
| major | Alta de turno (oscuro) | «Paciente: …» en azul `--color-primary` (≈3:1) y resultado elegido con fondo claro fijo | `--color-primary-deep` y `--color-primary-light` con variante oscura; 12.48:1 y 14:1 |
| blocker | Alta de turno (oscuro) | Resultados de búsqueda con el color negro del navegador sobre fondo oscuro (1.44:1) | `color: var(--color-text)` en `.agenda-resultado`; 14:1 |
| minor | Agenda (≤720 px) | Cabecera de la matriz visible por orden de reglas | `display: none` declarado después de `display: block` |
| minor | Agenda | «CONFIRMADO» partido en dos líneas | `overflow-wrap: break-word` en las tarjetas |

## Sin diferencias

- Las tres pantallas y los tres diálogos reproducen la estructura, jerarquía y estados del mockup aprobado (2026-11-12).
- 0 px de overflow horizontal en 390 y 1440 px, en claro y oscuro.
- Sin errores de consola, red ni excepciones; el 403 de la excepción es el estado verificado.
- Contraste AA (≥ 4.5:1) en todas las muestras, en ambos esquemas.
- Vista día apilada en mobile, semana en 7 columnas en desktop y lista en mobile.

## No verificado

- Diálogo de confirmación de llegada (`completado`): es el mismo componente que el de ausencia, sin el aviso de segunda falta.
- Estado 409 `estado_no_actualizable` dentro del diálogo: verificado por API end-to-end, no capturado.
- Alta con 409 `solape`: verificado por API y por los tests de `AltaTurnoDialog`; el alert usa la misma superficie ya medida.

## Artefactos

- Capturas: `mockups/verify/*.png` (páginas, diálogos y variantes `-dark`).
- Informes crudos: `informe-{light,dark}.json` (páginas) e `informe-dialogos-{light,dark}.json` (diálogos).
- Este resumen se regenera con el script temporal de recálculo de contraste (no versionado).
