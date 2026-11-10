# Spec — catalogo-practicas

## Purpose

Define el catálogo de prácticas odontológicas y sus aranceles, y el gobierno del porcentaje de seña por práctica que consumen el motor de reservas y el checkout.

## Requirements

### Requirement: Tipo de práctica como registro de catálogo

El sistema SHALL persistir cada práctica con `id`, `clinic_id`, `nombre`, `duracion_min`, `precio_base`, `sena_pct`, `activa` y los campos de auditoría, aislada por clínica.

#### Scenario: Alta de práctica en la clínica

- **WHEN** se crea una práctica con `nombre="Limpieza"`, `duracion_min=30`, `precio_base=15000` y `sena_pct=30`
- **THEN** el registro se guarda con `activa=true`, `is_active=true`, `created_at` y `updated_at` poblados

#### Scenario: Aislamiento por clínica

- **WHEN** existen prácticas de dos clínicas y se consulta el catálogo con un `clinic_id`
- **THEN** solo se devuelven las prácticas de esa clínica

### Requirement: Validación de duración y porcentaje de seña

Cada práctica SHALL rechazar `duracion_min` menor o igual a cero y un `sena_pct` fuera del rango cerrado 0 a 100.

#### Scenario: Duración inválida

- **WHEN** se intenta guardar una práctica con `duracion_min=0`
- **THEN** la operación falla por violación del CHECK `duracion_min > 0`

#### Scenario: Seña negativa

- **WHEN** se intenta guardar una práctica con `sena_pct=-1`
- **THEN** la operación falla por violación del CHECK de rango

#### Scenario: Seña mayor a cien

- **WHEN** se intenta guardar una práctica con `sena_pct=101`
- **THEN** la operación falla por violación del CHECK de rango

#### Scenario: Límites aceptados

- **WHEN** se guardan prácticas con `sena_pct=0` y `sena_pct=100`
- **THEN** ambas se persisten sin error

### Requirement: Arancel único por práctica

El sistema SHALL persistir un `Arancel` con `tipo_practica_id`, `precio`, `sena_pct` y `vigente_desde`, permitiendo como máximo un arancel por práctica.

#### Scenario: Segundo arancel para la misma práctica

- **WHEN** se intenta insertar un segundo arancel con un `tipo_practica_id` ya usado
- **THEN** la operación falla por violación del UNIQUE

#### Scenario: Arancel de práctica inexistente

- **WHEN** se inserta un arancel con un `tipo_practica_id` que no existe
- **THEN** la operación falla por violación de clave foránea

### Requirement: Precio efectivo de una práctica

El sistema SHALL resolver el precio efectivo de una práctica como el `precio` del arancel vigente a la fecha y, si no hay arancel, como su `precio_base`.

#### Scenario: Arancel vigente

- **WHEN** la práctica tiene un arancel con `precio=25000` vigente en la fecha consultada
- **THEN** el precio efectivo es 25000

#### Scenario: Sin arancel vigente

- **WHEN** la práctica no tiene arancel o su `vigente_desde` es posterior a la fecha consultada
- **THEN** el precio efectivo es su `precio_base`

#### Scenario: El porcentaje sale de la práctica

- **WHEN** se consulta el porcentaje de seña de una práctica con arancel asociado
- **THEN** el porcentaje devuelto es el `sena_pct` de la práctica

### Requirement: Lectura interna del catálogo de prácticas

El backend SHALL exponer `GET /api/internal/tipos-practica` para roles `recepcion`, `odonto` y `admin`, devolviendo las prácticas activas de la clínica del token.

#### Scenario: Recepción lista prácticas

- **WHEN** un usuario con rol `recepcion` llama al endpoint con un JWT válido
- **THEN** recibe 200 con las prácticas activas de su `clinic_id`

#### Scenario: Odontólogo lista prácticas

- **WHEN** un usuario con rol `odonto` llama al endpoint
- **THEN** recibe 200 con las prácticas activas de su clínica

#### Scenario: Sin token

- **WHEN** se llama al endpoint sin JWT
- **THEN** recibe 401

### Requirement: Lectura interna de sillones

El backend SHALL exponer `GET /api/internal/sillones` para roles `recepcion`, `odonto` y `admin`, devolviendo solo los sillones activos de la clínica del token.

#### Scenario: Listado de sillones activos

- **WHEN** un usuario interno autorizado llama al endpoint
- **THEN** recibe 200 con los sillones con `activo=true` de su clínica

#### Scenario: Sillón inactivo excluido

- **WHEN** la clínica tiene un sillón con `activo=false`
- **THEN** ese sillón no aparece en la respuesta

### Requirement: Lectura de aranceles por Admin

El backend SHALL exponer `GET /api/admin/aranceles` exclusivamente para rol `admin`, devolviendo por cada práctica su nombre, duración, precio efectivo y `% seña`.

#### Scenario: Admin consulta aranceles

- **WHEN** un usuario con rol `admin` llama al endpoint
- **THEN** recibe 200 con una entrada por práctica de su clínica

#### Scenario: Otro rol es rechazado

- **WHEN** un usuario con rol `recepcion` u `odonto` llama al endpoint
- **THEN** recibe 403

### Requirement: Actualización del porcentaje de seña

El backend SHALL exponer `PATCH /api/admin/tipos-practica/{id}/sena-pct` solo para rol `admin`, aceptando un valor entero entre 0 y 100.

#### Scenario: Admin actualiza el porcentaje

- **WHEN** el admin envía `sena_pct=40` para una práctica de su clínica
- **THEN** la respuesta es 200 y la práctica queda con 40

#### Scenario: Valor fuera de rango

- **WHEN** el admin envía `sena_pct=150` o un valor negativo
- **THEN** la respuesta es 422 y la práctica no cambia

#### Scenario: Práctica de otra clínica

- **WHEN** el admin intenta actualizar una práctica cuyo `clinic_id` no coincide con su token
- **THEN** la respuesta es 404 y no se modifica nada

#### Scenario: Otro rol es rechazado

- **WHEN** un usuario sin rol `admin` llama al endpoint de actualización
- **THEN** recibe 403

### Requirement: Auditoría de cambios de seña

Cada cambio de `% seña` SHALL registrar quién lo hizo, cuándo, el valor anterior y el valor nuevo en un registro append-only.

#### Scenario: Cambio auditado

- **WHEN** el admin cambia el `% seña` de 30 a 40
- **THEN** se crea un registro de auditoría con `usuario_id`, `valor_anterior=30`, `valor_nuevo=40` y `created_at`

#### Scenario: El cambio no reescribe turnos

- **WHEN** se actualiza el `% seña` de una práctica con turnos ya creados
- **THEN** los montos de seña de esos turnos permanecen sin cambios

### Requirement: Migración 004 del catálogo

La migración `004_catalogo_practicas` SHALL crear `tipos_practica`, `aranceles` y `auditorias_sena` con sus constraints e índices, sin reutilizar la revisión `003`.

#### Scenario: Upgrade crea las tablas

- **WHEN** `alembic upgrade head` corre sobre una base en revisión 003
- **THEN** existen `tipos_practica`, `aranceles` y `auditorias_sena` con sus CHECKs, UNIQUE e índices

#### Scenario: Downgrade revierte el catálogo

- **WHEN** `alembic downgrade -1` corre desde 004
- **THEN** las tres tablas se eliminan sin error y la base vuelve a 003

### Requirement: Seed inicial de prácticas

El seed SHALL crear de forma idempotente cinco prácticas —limpieza, arreglo, endodoncia, extracción y control de ortodoncia— cada una con duración, precio base, `% seña` provisorio y su arancel 1:1.

#### Scenario: Seed en base vacía

- **WHEN** el seed corre sobre una base sin prácticas
- **THEN** existen exactamente cinco prácticas con sus cinco aranceles

#### Scenario: Seed ejecutado dos veces

- **WHEN** el seed corre dos veces
- **THEN** no se duplican prácticas ni aranceles

### Requirement: Pantalla admin de aranceles

El frontend SHALL mostrar en `/admin` la lista real de prácticas con precio efectivo y `% seña`, y SHALL ofrecer un selector de práctica reutilizable por el flujo de reserva.

#### Scenario: Admin ve datos reales

- **WHEN** un usuario `admin` abre `/admin`
- **THEN** la tabla muestra las prácticas obtenidas de `GET /api/admin/aranceles`, sin datos hardcodeados

#### Scenario: Edición de seña acotada

- **WHEN** el admin edita el `% seña` de una práctica
- **THEN** el frontend envía el PATCH y refleja el valor confirmado por el backend

#### Scenario: Selector reutilizado por reserva

- **WHEN** el flujo de reserva necesita elegir una práctica
- **THEN** reutiliza el mismo componente selector de práctica que la pantalla admin

### Requirement: Cobertura de tests del catálogo

La suite SHALL cubrir constraints de duración y seña, unicidad de arancel, aislamiento por `clinic_id`, RBAC de lectura y escritura, auditoría y resolución de precio efectivo.

#### Scenario: Suite del catálogo pasa

- **WHEN** se ejecuta `pytest`
- **THEN** pasan los tests de modelos, migración 004, seed, endpoints y auditoría del catálogo
