# Identidad de marca — Turnos Odontología

Fundación visual **provisoria** del proyecto. Ninguna decisión marcada `(TBD)` debe
tratarse como final: están aisladas en rutas estables para poder reemplazarlas sin
tocar los mockups.

| Elemento | Valor actual | Fuente |
|---|---|---|
| Nombre de producto (UI) | `Turnos Odontología` | `frontend/index.html` (`<title>`, `meta description`) |
| Nombre comercial de la clínica | `(TBD)` | — |
| Idioma / locale | `es-AR`, voseo | `frontend/index.html` (`lang="es-AR"`) |
| Logo | `design-system/assets/logo.svg` — **provisorio, rotulado** | placeholder propio |
| Color de marca | `#2563eb` | `frontend/src/index.css` (`--color-primary`) |
| Tipografía | System UI stack (sin fuente remota) | `frontend/src/index.css` (`--font-sans`) |
| Tono de color del navegador | `#2563eb` | `frontend/index.html` (`theme-color`) |

## Voz y tono

- Español rioplatense, voseo ("reservá", "elegí", "podés"). Fuente: KB + textos de UI.
- Cercano y directo, sin jerga clínica innecesaria: el paciente reserva desde el
  teléfono en menos de 2 minutos, muchas veces sin contexto dental.
- Nunca culpabilizar al paciente en mensajes de error ni en cancelaciones.
- Mensajes de estado siempre con verbo + objeto: "Turno confirmado", "Seña
  acreditada", "Horario liberado".
- Los errores explican qué pasó y qué hacer a continuación; nunca muestran
  `traceback`, IDs internos ni el token completo.

## Logo

- Ruta estable: `design-system/assets/logo.svg`. Reemplazar ese archivo es el
  único paso para cambiar el logo en todos los mockups y previews.
- El archivo actual es un **placeholder rotulado "LOGO PROVISORIO"** con un diente
  en el azul de marca. No es una marca aprobada.
- Usos: header público (hasta 32 px de alto), favicon (`(TBD)`, hoy
  `frontend/public/favicon.svg` es un asset violeta ajeno a la marca — reemplazar).
- Área de resguardo: alto del ícono. No rotar, no recolorear fuera de la paleta,
  no aplicar sombras ni degradados al logo.
- Versión monocroma / para fondo oscuro: `(TBD)`.

## Imágenes

- La app es mobile-first y de bajo peso: preferir ilustración simple o fotografía
  clínica neutra; nunca stock con texto incrustado.
- Toda imagen decorativa va con `alt=""`; las informativas describen la acción.
- Hero actual usa degradé de marca, no fotografía (`frontend/src/pages/HomePage.css`).
- Fotografía de la clínica / profesionales: `(TBD)` — depende de assets del cliente.

## Reglas de uso del color

- Azul de marca reservado a acción primaria, foco y enlaces. No usar azul para
  transmitir estado (para eso están success/warning/danger).
- Estados del turno: `pendiente_sena` → warning, `confirmado` → success,
  `cancelado` / `ausente` → neutral-dangereado, `atendido` → info. El estado nunca
  se comunica **solo** por color: siempre color + etiqueta de texto.
- Contraste mínimo AA: 4.5:1 en texto, 3:1 en límites de controles y foco.
  `--color-text-muted` queda **solo para elementos decorativos** (2.54:1 en blanco):
  nunca para texto que deba leerse. El texto auxiliar, las etiquetas mono y los
  placeholders usan `--color-text-secondary` / `--color-text-placeholder`.
- Controles deshabilitados quedan exentos de AA (WCAG 1.4.3) y por eso pueden
  verse deliberadamente apagados — pero siempre acompañados de `disabled` real,
  no solo de color.

## Movimiento

- Un solo lenguaje: 150 ms (micro-interacciones) y 250 ms (transiciones de estado).
- Nada de animaciones de entrada por scroll ni parallax.
- Respeto obligatorio de `prefers-reduced-motion` (`tokens.css` ya lo neutraliza).
- El cambio de horario seleccionado se comunica con color **y** borde/ícono.

## Accesibilidad

- Área táctil mínima 44×44 px (`--touch-target`); controles de formulario 48 px.
- Foco visible siempre (`--focus-ring-width` + `--focus-ring-offset`), nunca
  `outline: none` sin reemplazo.
- Un solo `h1` por pantalla; jerarquía sin saltos.
