# Evidencia de uso del MCP filesystem

## Herramientas disponibles

- `read_file`: Read the complete contents of a file as text. DEPRECATED: Use read_text_file instead.
- `read_text_file`: Read the complete contents of a file from the file system as text. Handles various text encodings and provides detailed error messages if the file cannot be read. Use this tool when you need to examine the contents of a single file. Use the 'head' parameter to read only the first N lines of a file, or the 'tail' parameter to read only the last N lines of a file. Operates on the file as text regardless of extension. Only works within allowed directories.
- `read_media_file`: Read a file and return it as a base64-encoded content block with its MIME type. Image and audio files are returned as image/audio content; any other file type is returned as an embedded resource. Only works within allowed directories.
- `read_multiple_files`: Read the contents of multiple files simultaneously. This is more efficient than reading files one by one when you need to analyze or compare multiple files. Each file's content is returned with its path as a reference. Failed reads for individual files won't stop the entire operation. Only works within allowed directories.
- `write_file`: Create a new file or completely overwrite an existing file with new content. Use with caution as it will overwrite existing files without warning. Handles text content with proper encoding. Only works within allowed directories.
- `edit_file`: Make line-based edits to a text file. Each edit replaces exact line sequences with new content. Returns a git-style diff showing the changes made. Only works within allowed directories.
- `create_directory`: Create a new directory or ensure a directory exists. Can create multiple nested directories in one operation. If the directory already exists, this operation will succeed silently. Perfect for setting up directory structures for projects or ensuring required paths exist.
- `list_directory`: Get a detailed listing of all files and directories in a specified path. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is essential for understanding directory structure and finding specific files within a directory.
- `list_directory_with_sizes`: Get a detailed listing of all files and directories in a specified path, including sizes. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is useful for understanding directory structure and finding specific files within a project.
- `directory_tree`: Get a recursive tree view of files and directories as a JSON structure. Each entry includes 'name', 'type' (file/directory), and 'children' for directories. Files have no children array, while directories always have a children array (which may be empty). The output is formatted with 2-space indentation for readability. Only works within allowed directories.
- `move_file`: Move or rename files and directories. Can move files between directories and rename them in a single operation. If the destination exists, the operation will fail. Works across different directories and can be used for simple renaming within the same directory. Both source and destination must be within allowed directories.
- `search_files`: Recursively search for files and directories matching a pattern. The patterns should be glob-style patterns that match paths relative to the working directory. Use pattern like '*.ext' to match files in current directory, or '**/*.ext' to match files in all subdirectories. Returns full paths to all matching items. Great for finding files when you don't know their exact location. Only searches within allowed directories.
- `get_file_info`: Retrieve detailed metadata about a file or directory. Returns comprehensive information including size, creation time, last modified time, permissions, type and hard-link count. This tool is perfect for understanding file characteristics without reading the actual content.
- `list_allowed_directories`: Returns the list of directories that this server is allowed to access. Subdirectories within these allowed directories are also accessible. Use this to understand which directories and their nested paths are available before trying to access files.

## Resultado: list_directory (raíz del proyecto)

```
[FILE] .active-orchestrator-state.json
[DIR] .atl
[DIR] .github
[DIR] .opencode
[FILE] AGENTS.md
[DIR] backend
[FILE] CHANGES.md
[FILE] CLAUDE.md
[DIR] discovery
[FILE] docker-compose.ci.yml
[FILE] docker-compose.yml
[DIR] docs
[DIR] frontend
[DIR] knowledge-base
[DIR] openspec
[DIR] skills
```

## Resultado: read_text_file (05_reglas_de_negocio.md, primeras 50 líneas)

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

## Dominio: Ausentismo / bloqueo (RN-AUS)

- **RN-AUS-01**: 2 faltas (`estado=ausente` marcado por recepción) → bloqueo de reserva por 30 días (`bloqueado_hasta = now() + 30d`). Decisión ronda 1 (respuesta 4).
- **RN-AUS-02**: Paciente bloqueado no puede crear reservas (público e interno lo rechazan); recepción puede exceptuar con auditoría (motivo obligatorio).
- **RN-AUS-03**: La falta la marca recepción/odontólogo desde panel del día (no automática).

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

## Conclusión

El servidor MCP filesystem se conectó correctamente, expuso 12 herramientas y respondió a las herramientas ejecutadas.