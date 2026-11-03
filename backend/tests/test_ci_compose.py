"""Guards del stack de CI: el smoke test corre en el host y necesita la API publicada."""

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = REPO_ROOT / "docker-compose.ci.yml"
SMOKE_SCRIPT_PATH = REPO_ROOT / "scripts" / "ci" / "smoke-test.sh"


def _load_compose() -> dict:
    with COMPOSE_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _published_host_ports(service: dict) -> set[str]:
    ports: set[str] = set()
    for entry in service.get("ports", []):
        if isinstance(entry, dict):
            published = entry.get("published")
            if published is not None:
                ports.add(str(published))
            continue
        parts = str(entry).split(":")
        ports.add(parts[-2] if len(parts) > 1 else parts[0])
    return ports


def _smoke_test_health_url_port() -> str:
    script = SMOKE_SCRIPT_PATH.read_text(encoding="utf-8")
    match = re.search(r'HEALTH_URL="\$\{HEALTH_URL:-http://localhost:(\d+)', script)
    assert match is not None, "No se pudo leer el puerto por defecto de HEALTH_URL"
    return match.group(1)


def test_ci_compose_publishes_api_port_on_host() -> None:
    compose = _load_compose()

    assert "8000" in _published_host_ports(compose["services"]["api"])


def test_smoke_test_health_url_port_is_published_by_compose() -> None:
    compose = _load_compose()
    health_port = _smoke_test_health_url_port()

    assert health_port in _published_host_ports(compose["services"]["api"])
