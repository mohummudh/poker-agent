from __future__ import annotations

import os
from pathlib import Path


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and ((value[0] == "'" and value[-1] == "'") or (value[0] == '"' and value[-1] == '"')):
        return value[1:-1]
    return value


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        env_key = key.strip()
        env_value = _strip_quotes(value.strip())
        if not env_key:
            continue

        # Shell/exported env vars win over file values.
        os.environ.setdefault(env_key, env_value)


def load_environment() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    project_root = backend_root.parent

    _load_env_file(project_root / ".env")
    _load_env_file(backend_root / ".env")
