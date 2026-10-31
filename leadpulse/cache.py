"""Tiny on-disk JSON cache for LLM results (same lead -> same explanation, no repeat calls)."""

import hashlib
import json
from pathlib import Path
from typing import Any

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "llm"


def cache_key(*parts: str) -> str:
    """Stable key from the parts (input hash, scoring version, prompt version, model)."""
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def get(key: str) -> dict[str, Any] | None:
    """Return the cached JSON for key, or None if absent or unreadable."""
    try:
        return json.loads((CACHE_DIR / f"{key}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def put(key: str, data: dict[str, Any]) -> None:
    """Store data under key. A read-only disk just means no caching, never an error."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (CACHE_DIR / f"{key}.json").write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass
