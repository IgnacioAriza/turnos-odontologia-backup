# Evidencia de uso del MCP filesystem — C-08 pagos-seguridad

## Herramientas disponibles

- `read_file`: Read the complete contents of a file as text. DEPRECATED: Use read_text_file instead.
- `read_text_file`: Read the complete contents of a file from the file system as text. Handles various text encodings and provides detailed error messages if the file cannot be read. Use this tool when you need to examine the contents of a single file. Use the 'head' parameter to read only the first N lines of a file, or the 'tail' parameter to read only the last N lines of a file. Operates on the file as text regardless of extension. Only works within allowed directories.
- `read_media_file`: Read a file and return it as a base64-encoded content block with its MIME type. Image and audio files are returned as image/audio content; any other file type is returned as an embedded resource. Only works within allowed directories.
- `read_multiple_files`: Read the contents of multiple files simultaneously. This is more efficient than reading files one by one when you need to analyze or compare multiple files. Each file's content is returned with its path as a reference. Failed reads for individual files won't stop the entire operation. Only works within allowed directories.
- `write_file`: Create a new file or completely overwrite an existing file with new content. Use with caution as it will overwrite existing files without warning. Handles text content with proper encoding. Only works within allowed directories.
- `edit_file`: Make line-based edits to a text file. Each edit replaces exact line sequences with new content. Returns a git-style diff showing the changes made. Only works within allowed directories.
- `create_directory`: Create a new directory or ensure a directory exists. Can create multiple nested directories in one operation. If the directory already exists, this operation will succeed silently. Perfect for setting up directory structures for projects or ensuring required paths exist.
- `list_directory`: Get a detailed listing of all files and directories in a specified path. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is essential for understanding directory structure and finding specific files within a project.
- `list_directory_with_sizes`: Get a detailed listing of all files and directories in a specified path, including sizes. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is useful for understanding directory structure and finding specific files within a project.
- `directory_tree`: Get a recursive tree view of files and directories as a JSON structure. Each entry includes 'name', 'type' (file/directory), and 'children' for directories. Files have no children array, while directories always have a children array (which may be empty). The output is formatted with 2-space indentation for readability. Only works within allowed directories.
- `move_file`: Move or rename files and directories. Can move files between directories and rename them in a single operation. If the destination exists, the operation will fail. Works across different directories and can be used for simple renaming within the same directory. Both source and destination must be within allowed directories.
- `search_files`: Recursively search for files and directories matching a pattern. The patterns should be glob-style patterns that match paths relative to the working directory. Use pattern like '*.ext' to match files in current directory, or '**/*.ext' to match files in all subdirectories. Returns full paths to all matching items. Great for finding files when you don't know their exact location. Only searches within allowed directories.
- `get_file_info`: Retrieve detailed metadata about a file or directory. Returns comprehensive information including size, creation time, last modified time, permissions, type and hard-link count. This tool is perfect for understanding file characteristics without reading the actual content.
- `list_allowed_directories`: Returns the list of directories that this server is allowed to access. Subdirectories within these allowed directories are also accessible. Use this to understand which directories and their nested paths are available before trying to access files.

## Resultado: read_text_file (knowledge-base/11_pagos_mercadopago.md, primeras 60 líneas)

# Pagos con Mercado Pago (extra v1.0)

Complementa `05_reglas_de_negocio.md` (RN-PAGO-*) y `07_flujos_principales.md` (Flujos 1 y 4). Alcance: seña en % REAL en el MVP.

## Configuración

- Cuenta MP de la clínica; `MP_ACCESS_TOKEN` + `MP_WEBHOOK_SECRET` en env (ver `08_arquitectura_propuesta.md`).
- Moneda ARS; `monto_sena = round(precio_base * sena_pct / 100)` fotografiado en `Turno.monto_sena` (RN-PAGO-02).
- Preference por reserva: `external_reference = turno_id`, `metadata = {clinic_id, turno_id, idempotency_key}`.

## Webhook

- `POST /api/webhooks/mercadopago`: valida firma, busca `mp_payment_id`; si existe → 200 sin efectos (RN-PAGO-03).
- Solo `estado=aprobado` confirma el turno (`pendiente_sena → confirmado`) y dispara WA + job T-24hs.
- Guarda `raw_webhook` (jsonb) para auditoría/conciliación.
- Reintentos MP: endpoint idempotente + worker de reproceso (US-008).

## Reembolsos (según RN-CANCEL-*)

- 1.ª reprogramación: la seña migra (sin movimiento MP).
- Cancelación en ventana o 2.ª reprogramación / tardía: seña no reembolsable (política visible antes de pagar).
- Reembolso manual solo por Admin con motivo auditado (excepción, no flujo normal).

## Riesgos

- Fricción/abandono checkout (SU-01): medir tasa de abandono; considerar alias/CVU y montos redondeados.
- Contracargos y conciliación diaria (US-008, pregunta Media en `10_preguntas_abiertas.md`).

## Resultado: read_text_file (knowledge-base/05_reglas_de_negocio.md, primeras 60 líneas)

# Reglas de Negocio

Cada regla tiene código único `RN-{DOMINIO}-{NN}` para trazabilidad (usado en `06_funcionalidades.md` y `07_flujos_principales.md`).

## Dominio: Reservas (RN-RES)

- **RN-RES-01**: Un sillón no puede tener dos turnos superpuestos (mismo `sillon_id`, rangos `[inicio, fin)` intersectados → rechazo 409).
- **RN-RES-02**: Un odontólogo no puede tener dos turnos superpuestos (misma condición sobre `odontologo_id`).
- **RN-RES-03**: La reserva pública no exige login; emite `manage_token` para gestión posterior.
- **RN-RES-04**: Todo turno nace en `pendiente_sena` con expiración (TTL a definir, propuesto 30 min); sin seña aprobada en ventana → se libera el slot.
- **RN-RES-05**: Solo pasa a `confirmado` con `Pago.estado=aprobado` (webhook MP).

## Dominio: Cancelación / reprogramación (RN-CANCEL)

- **RN-CANCEL-01**: Cancelación mínima 12hs de anticipación (`inicio - now() >= 12h`).
- **RN-CANCEL-02**: 1 reprogramación sin perder seña por turno (`reprogramaciones_count < 1`, nuevo horario con misma anticipación 12hs); la seña viaja al nuevo turno.
- **RN-CANCEL-03**: 2.ª reprogramación o cancelación tardía (< 12hs) → seña no reembolsable; el slot se libera igual.
- **RN-CANCEL-04**: Cancelar/reprogramar libera el horario inmediatamente para re-reserva.

## Dominio: Pagos / seña (RN-PAGO)

- **RN-PAGO-01**: Seña en % del precio de la práctica, según `TipoPractica.sena_pct`, configurable por Admin.
- **RN-PAGO-02**: `monto_sena = round(precio_base * sena_pct / 100)` al crear la reserva (foto del monto en `Turno.monto_sena`; cambios posteriores de arancel no alteran turnos existentes).
- **RN-PAGO-03**: Webhook MP idempotente (`mp_payment_id` / `idempotency_key` UNIQUE; reprocesos no duplican confirmación).
- **RN-PAGO-04**: Un solo pago aprobado vigente por turno.

## Dominio: Notificaciones (RN-NOTIF)

- **RN-NOTIF-01**: Recordatorio WhatsApp 24hs antes, UN solo envío por turno confirmado (`scheduled_for = inicio - 24h`).
- **RN-NOTIF-02**: Confirmación inmediata por WA + respaldo email al aprobarse la seña.
- **RN-NOTIF-03**: Si el turno se cancela/reprograma antes de T-24hs, el job programado se cancela (no enviar recordatorio de turno muerto).
- **RN-NOTIF-04**: Proveedor Twilio con número transparente de la clínica (decisión ronda 1).

## Dominio: Administración (RN-ADMIN)

- **RN-ADMIN-01**: Solo `admin` modifica `% seña` y (v1.1) aranceles; todo cambio audita `quien/cuando/antes/después`.
- **RN-ADMIN-02**: En v1.0 aranceles son lectura + seed inicial; el CRUD llega en v1.1 (ver IN-01).

## Dominio: Excepciones globales

- Toda validación de solape, ventana 12hs y bloqueo se evalúa en `America/Argentina/Buenos_Aires`.
- Errores de MP/Twilio nunca dejan el turno en estado ambiguo: `pendiente_sena` + reintento con backoff; auditoría en `Pago.raw_webhook` / `Notificacion.estado=fallido`.
- Recepción puede operar por teléfono/presencial creando el turno como interno (mismo motor de reglas, sin `manage_token` público).

## Resultado: read_text_file (knowledge-base/08_arquitectura_propuesta.md, primeras 60 líneas)

# Arquitectura Propuesta

## Patrones aplicados

| Patrón | Dónde se usa | Por qué |
|---|---|---|
| Monolito modular por dominios | Backend (routers `turnos`, `pagos`, `notificaciones`, `admin`) | Prioridad escalabilidad (ronda 1): separa para partir a servicios sin pagar microservicios día 1 |
| REST + webhooks idempotentes | MP/Twilio inbound | Pagos y entregas con reintentos exigen idempotencia |
| Job queue + scheduler | Redis (WA T-24hs, expiración `pendiente_sena`) | Desacopla envío programado del request |
| RBAC por rol | JWT claims `rol` + guards por router | 4 roles, sin ABAC en v1 |
| Foto de precio en turno | `Turno.monto_sena` | Cambios de arancel no reescriben historia |
| Soft states + auditoría | `estado`, `raw_webhook`, `Bloqueo.created_by` | Trazabilidad pagos/bloqueos/excepciones |

## Variables de entorno

| Variable | Descripción | Ejemplo | Sensible |
|---|---|---|---|
| `MP_ACCESS_TOKEN` | Credencial Mercado Pago | `APP_USR-...` | Y |
| `MP_WEBHOOK_SECRET` | Firma webhook MP | `...` | Y |
| `MP_TTL_MIN` | Expiración `pendiente_sena` | `30` | N |

## Resultado: read_text_file (CHANGES.md, primeras 60 líneas)

# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto **SaaS Odontología (turnos 24/7 + seña MP + WA Twilio)**.
> Cada change es atómico: un agente puede implementarlo en una sesión (~4-6 horas).
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**

> Oleadas: **v1.0 MVP lanzable (US-001–009)** = reserva 24/7 + agenda multi-sillón + cancel/reprog + panel día + seña % MP real + WA 24hs real. **v1.1 fast-follow (US-010–012)** = login paciente + odontograma + ABM aranceles. Respeta **IN-01** (`knowledge-base/10_preguntas_abiertas.md`): Discovery pedía todo en v1, ronda 1 3b lo partió en dos oleadas.

## Árbol de dependencias

```
C-08 checkout-sena-mercadopago     ← paralelo con C-06/C-07
  └── C-09 webhook-conciliacion
        └── C-10 notificaciones-whatsapp-twilio *
```

Camino crítico (8): `C-01 → C-02 → C-03 → C-04 → C-05 → C-08 → C-09 → C-10`

## Resultado: list_directory (backend/app/domain/pagos)

[DIR] __pycache__
[FILE] __init__.py

## Resultado: list_directory (backend/app/api/webhooks)

[DIR] __pycache__
[FILE] __init__.py

## Conclusión

El servidor MCP filesystem se conectó correctamente, expuso 13 herramientas y respondió a las herramientas ejecutadas sobre los archivos de pagos del proyecto. Se pudo leer el KB de pagos (`11_pagos_mercadopago.md`), las reglas de negocio (`05_reglas_de_negocio.md`), las variables de entorno (`08_arquitectura_propuesta.md`) y el roadmap (`CHANGES.md`), confirmando que los directorios `backend/app/domain/pagos/` y `backend/app/api/webhooks/` existen pero están vacíos (solo `__init__.py`), consistente con que C-08 aún no está implementado y solo se prepara su especificación.