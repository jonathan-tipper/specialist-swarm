"""Create-once persistence for agent, environment, skill, and session IDs.

Managed Agents resources are persistent and versioned. Creating them fresh on
every run accumulates orphans and defeats version pinning, so every setup step
routes through here: look up first, create only on a miss.
"""

import json
from pathlib import Path
from typing import Any, Callable

DEFAULT_PATH = Path(".swarm_ids.json")


class IdStore:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = Path(path)

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text())
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{self.path} is not valid JSON ({exc}). Delete it to start over."
            ) from exc

    def _save(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

    def get(self, key: str) -> Any:
        """Read a value. Dotted keys index into nested dicts."""
        node: Any = self._load()
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        return node

    def set(self, key: str, value: Any) -> None:
        """Write a value. Dotted keys create intermediate dicts."""
        data = self._load()
        parts = key.split(".")
        node = data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
        self._save(data)

    def get_or_create(self, key: str, factory: Callable[[], Any]) -> tuple[Any, bool]:
        """Return (value, created). Calls `factory` only when the key is absent."""
        existing = self.get(key)
        if existing is not None:
            return existing, False
        value = factory()
        self.set(key, value)
        return value, True
