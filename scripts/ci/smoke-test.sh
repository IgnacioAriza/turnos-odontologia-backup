#!/usr/bin/env bash
#
# Smoke test E2E del backend sobre docker-compose.ci.yml.
#
# Levanta el stack, espera activamente a que /api/health responda 200,
# verifica que PostgreSQL y Redis estén conectados y garantiza el teardown
# del stack incluso si el test falla.
#
# Uso: bash scripts/ci/smoke-test.sh [timeout_segundos]
#
# Variables opcionales:
#   HEALTH_URL        URL del healthcheck (default: http://localhost:8000/api/health)
#   RETRY_INTERVAL    Segundos entre reintentos (default: 2)
#   COMPOSE_FILE      Ruta al compose (default: <repo>/docker-compose.ci.yml)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

COMPOSE_FILE="${COMPOSE_FILE:-${REPO_ROOT}/docker-compose.ci.yml}"
HEALTH_URL="${HEALTH_URL:-http://localhost:8000/api/health}"
TIMEOUT_SECONDS="${1:-180}"
RETRY_INTERVAL="${RETRY_INTERVAL:-2}"

HEALTH_BODY="$(mktemp)"

compose() {
  docker compose -f "${COMPOSE_FILE}" "$@"
}

dump_diagnostics() {
  echo "::group::docker compose ps"
  compose ps || true
  echo "::endgroup::"

  echo "::group::api logs"
  compose logs --no-color --tail=200 api || true
  echo "::endgroup::"

  echo "::group::worker logs"
  compose logs --no-color --tail=100 worker || true
  echo "::endgroup::"
}

cleanup() {
  local status=$?
  rm -f "${HEALTH_BODY}" || true
  echo "==> Tearing down compose stack (down -v --remove-orphans)"
  compose down -v --remove-orphans || true
  return "${status}"
}
trap cleanup EXIT

echo "==> Building and starting stack (${COMPOSE_FILE})"
if ! compose up -d --build; then
  echo "::error::docker compose up falló"
  dump_diagnostics
  exit 1
fi

echo "==> Waiting for ${HEALTH_URL} (timeout: ${TIMEOUT_SECONDS}s, interval: ${RETRY_INTERVAL}s)"
deadline=$((SECONDS + TIMEOUT_SECONDS))
attempt=0
http_code=""

while ((SECONDS < deadline)); do
  attempt=$((attempt + 1))
  # -w escribe el status code; -o guarda el body para validarlo luego.
  http_code="$(curl -sS -o "${HEALTH_BODY}" -w '%{http_code}' --max-time 5 "${HEALTH_URL}" 2>/dev/null || true)"
  if [[ "${http_code}" == "200" ]]; then
    echo "==> API respondió 200 en el intento ${attempt} ($((${SECONDS} - (deadline - TIMEOUT_SECONDS)))s)"
    break
  fi
  echo "    intento ${attempt}: HTTP '${http_code:-sin respuesta}' — reintentando en ${RETRY_INTERVAL}s"
  sleep "${RETRY_INTERVAL}"
done

if [[ "${http_code}" != "200" ]]; then
  echo "::error::La API no respondió 200 en ${TIMEOUT_SECONDS}s (último código: '${http_code:-sin respuesta}')"
  dump_diagnostics
  exit 1
fi

echo "==> Validating PostgreSQL and Redis connectivity"
python3 - "${HEALTH_BODY}" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as fh:
    payload = json.load(fh)

errors = []
if payload.get("status") != "ok":
    errors.append(f"status={payload.get('status')!r}")
for dependency in ("database", "redis"):
    if payload.get(dependency) != "connected":
        errors.append(f"{dependency}={payload.get(dependency)!r}")

if errors:
    print("Healthcheck inválido: " + ", ".join(errors))
    sys.exit(1)

print("Healthcheck OK: " + json.dumps(payload, ensure_ascii=False))
PY

echo "==> Smoke test passed (API, PostgreSQL y Redis OK)"
