# Spec Delta — booking-publico

## Purpose

Define la experiencia web pública mobile-first con la que un paciente busca horarios, reserva con su teléfono y gestiona su turno por token sin crear cuenta.

## ADDED Requirements

### Requirement: Catálogo público de prácticas

El backend SHALL exponer `GET /api/public/practicas` para que la landing liste las prácticas reservables sin requerir sesión ni UUIDs conocidos de antemano, y el frontend SHALL alimentar el selector desde ese endpoint sin listas hardcodeadas.

#### Scenario: Listado público de prácticas activas

- **WHEN** un visitante sin sesión abre `/`
- **THEN** el selector se llena con las prácticas con `activa = true` devueltas por `GET /api/public/practicas`, ordenadas por `nombre`, con `id`, `nombre`, `duracion_min` y `sena_pct`

#### Scenario: Datos no públicos fuera del catálogo

- **WHEN** se inspecciona la respuesta de `GET /api/public/practicas`
- **THEN** no incluye `precio_base`, aranceles, `clinic_id`, prácticas inactivas ni ningún dato interno de la clínica

#### Scenario: Catálogo vacío

- **WHEN** no hay prácticas activas cargadas
- **THEN** la landing muestra un estado explícito de "sin prácticas disponibles" con el canal de contacto de la clínica, en lugar de un selector vacío o un error técnico

#### Scenario: La práctica elegida alimenta la búsqueda de horarios

- **WHEN** el paciente elige una práctica del catálogo
- **THEN** la consulta a `GET /api/public/slots` usa el `id` devuelto por el catálogo, sin que el frontend construya ni traduzca identificadores

### Requirement: Landing pública con búsqueda de horarios

El frontend SHALL ofrecer en la ruta `/` una búsqueda de horarios libres por fecha y práctica, usable desde un teléfono sin iniciar sesión.

#### Scenario: Búsqueda sin sesión

- **WHEN** un visitante sin sesión abre `/`, elige una práctica y una fecha
- **THEN** ve la lista de horarios libres devuelta por el backend, en la hora local de la clínica

#### Scenario: Día sin horarios

- **WHEN** la fecha consultada no tiene horarios libres
- **THEN** la pantalla muestra un mensaje explícito y sugiere probar otra fecha, sin quedar en blanco

#### Scenario: Error del backend

- **WHEN** la consulta de horarios falla
- **THEN** la pantalla muestra un error legible con opción de reintentar, sin exponer detalles técnicos

#### Scenario: Visitante con sesión iniciada en la landing

- **WHEN** un usuario interno autenticado abre `/`
- **THEN** la aplicación lo redirige a su panel y no entra en un ciclo de redirecciones

### Requirement: Reserva con teléfono en formato argentino

El frontend SHALL pedir nombre y teléfono, SHALL normalizar el teléfono al formato E.164 argentino y SHALL impedir el envío cuando el número no sea válido.

#### Scenario: Teléfono válido

- **WHEN** el paciente escribe `11 5555 1234`
- **THEN** el formulario envía el teléfono normalizado como `+5491155551234`

#### Scenario: Teléfono inválido

- **WHEN** el paciente escribe un número con menos dígitos que un teléfono argentino completo
- **THEN** el formulario muestra el error en el campo y no envía la reserva

#### Scenario: Reserva creada

- **WHEN** el paciente confirma una reserva con datos válidos y un horario libre
- **THEN** la pantalla muestra el turno creado en estado pendiente de seña, su horario y el enlace de gestión

#### Scenario: Horario tomado en el último momento

- **WHEN** el backend responde 409 por solape
- **THEN** la pantalla avisa que el horario se ocupó, refresca los horarios disponibles y conserva los datos ya cargados, identificando el caso por el `codigo` estable del problem+json y no por el texto del mensaje

### Requirement: Entrega al checkout de la seña

El frontend SHALL entregar la reserva creada al flujo de pago de la seña y SHALL mostrar un estado de pago pendiente cuando el cobro todavía no está disponible.

#### Scenario: Redirección al checkout

- **WHEN** el backend devuelve una URL de pago para el turno
- **THEN** la pantalla redirige al paciente a Mercado Pago

#### Scenario: Checkout todavía no disponible

- **WHEN** el cobro de la seña no está implementado en el entorno
- **THEN** la pantalla muestra el turno como pendiente de seña con su enlace de gestión, sin bloquear la reserva ni simular un pago aprobado

### Requirement: Pantalla de gestión por token

El frontend SHALL mostrar en `/gestionar/:token` el detalle del turno y SHALL ofrecer cancelar y reprogramar solo cuando el estado y la ventana lo permiten.

#### Scenario: Vista del turno

- **WHEN** el paciente abre su enlace de gestión
- **THEN** ve fecha, hora, práctica, estado de la seña y cuántas reprogramaciones le quedan sin costo

#### Scenario: Token inválido

- **WHEN** el token no corresponde a ningún turno
- **THEN** la pantalla muestra el mensaje de enlace inválido o vencido y no redirige a `/login`

#### Scenario: Acciones no disponibles

- **WHEN** el turno está cancelado, completado o ausente
- **THEN** la pantalla muestra el estado y oculta las acciones de cancelar y reprogramar

#### Scenario: Reprogramar por primera vez

- **WHEN** el paciente elige un horario nuevo dentro de la ventana
- **THEN** la pantalla confirma que la seña se mantiene y muestra el turno en su nuevo horario

### Requirement: Confirmación explícita de pérdida de seña

El frontend SHALL advertir antes de ejecutar una acción que pierde la seña y SHALL exigir una confirmación explícita del paciente.

#### Scenario: Cancelación tardía

- **WHEN** el paciente intenta cancelar dentro de las 12 horas previas
- **THEN** la pantalla advierte que la seña no se devuelve y solo ejecuta la cancelación tras confirmar

#### Scenario: Segunda reprogramación

- **WHEN** el paciente ya usó su reprogramación sin costo e intenta reprogramar otra vez
- **THEN** la pantalla advierte que necesita una seña nueva, y tras confirmar muestra el turno nuevo en estado pendiente de seña

#### Scenario: Paciente desiste de la confirmación

- **WHEN** el paciente cierra la advertencia sin confirmar
- **THEN** el turno no cambia y la pantalla vuelve al detalle previo

### Requirement: Comportamiento mobile-first de la experiencia pública

Las pantallas públicas SHALL funcionar en un viewport de 390x844 sin scroll horizontal, alcanzar los objetivos táctiles mínimos y no requerir sesión en ninguna acción pública.

#### Scenario: Reserva completa desde el teléfono

- **WHEN** el paciente recorre `/` y `/reservar` en un teléfono de 390 píxeles de ancho
- **THEN** completa la reserva sin scroll horizontal y sin acciones que exijan un mouse

#### Scenario: Carga en red móvil

- **WHEN** la búsqueda de horarios se ejecuta en una red móvil lenta
- **THEN** la pantalla muestra un indicador de carga y no parece congelada

### Requirement: Cobertura de tests del frontend público

La suite del frontend SHALL cubrir la búsqueda, el formulario de reserva con validación de teléfono, el estado de token inválido y los dos flujos de confirmación de pérdida de seña.

#### Scenario: Suite pública pasa

- **WHEN** se ejecuta el runner de tests del frontend
- **THEN** pasan los tests de las pantallas públicas y la compilación de tipos no reporta errores
