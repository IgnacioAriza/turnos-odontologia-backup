# Spec Delta

## Purpose

Provides a Vite React TypeScript SPA with mobile-first architecture, feature-based organization, and role-based routing for public and protected areas.

## ADDED Requirements

### Requirement: Vite React TypeScript project scaffold
The frontend SHALL be a Vite project with React 18, TypeScript 5, and strict TypeScript configuration.

#### Scenario: Project builds successfully
- **WHEN** running `npm run build`
- **THEN** build completes without TypeScript errors

#### Scenario: TypeScript strict mode enabled
- **WHEN** checking `tsconfig.json`
- **THEN** `strict: true` and all strict family options are enabled

### Requirement: Feature-based directory structure
The frontend SHALL organize code under `src/features/` with domain-aligned features: `booking/`, `agenda/`, `panel-dia/`, `admin/`, plus `shared/` for common utilities and `pages/` for route components.

#### Scenario: Feature directories exist
- **WHEN** the frontend project is scaffolded
- **THEN** directories `src/features/booking`, `src/features/agenda`, `src/features/panel-dia`, `src/features/admin`, `src/shared`, `src/pages` exist

#### Scenario: Shared API client available
- **WHEN** importing from `src/shared/api-client`
- **THEN** a configured Axios/Fetch client with base URL and interceptors is exported

### Requirement: Mobile-first responsive design
The frontend SHALL use a mobile-first approach with CSS that works on small screens first and scales up.

#### Scenario: Viewport meta tag present
- **WHEN** loading the app in a mobile browser
- **THEN** `<meta name="viewport" content="width=device-width, initial-scale=1">` is present

#### Scenario: Touch targets meet minimum size
- **WHEN** inspecting interactive elements
- **THEN** minimum touch target size is 44x44 CSS pixels

### Requirement: Role-based routing
The frontend SHALL have a router that separates public routes (booking, slot search, appointment management via token) from protected routes (agenda, panel, admin) requiring JWT authentication with role claims.

#### Scenario: Public routes accessible without auth
- **WHEN** navigating to `/`, `/reservar`, `/gestionar/:token`
- **THEN** pages render without redirecting to login

#### Scenario: Protected routes redirect unauthenticated users
- **WHEN** unauthenticated user navigates to `/agenda`, `/panel`, `/admin`
- **THEN** user is redirected to `/login` with return URL preserved

#### Scenario: Role guards enforce permissions
- **WHEN** authenticated user with role `recepcion` accesses `/admin`
- **THEN** access is denied (403 or redirect)

#### Scenario: Odontólogo role confined to own data
- **WHEN** authenticated user with role `odonto` accesses `/agenda`
- **THEN** only appointments for their `odontologo_id` are visible

### Requirement: Environment-based API configuration
The frontend SHALL read API base URL from `VITE_API_URL` environment variable with a development default.

#### Scenario: API URL configurable
- **WHEN** `VITE_API_URL` is set in `.env`
- **THEN** all API requests use that base URL

#### Scenario: Development default works
- **WHEN** no `VITE_API_URL` is set
- **THEN** API client defaults to `http://localhost:8000`