"""Loads the scoring YAML once and checks that the weights add up to 100."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

CONFIG_PATH = Path(__file__).parent / "config" / "scoring_config.yaml"


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    """Return the parsed scoring config. Raises ValueError if the weights do not total 100."""
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    total = sum(p["max"] for p in config["parameters"].values())
    if total != 100:
        raise ValueError(f"Parameter weights must total 100, got {total}")
    return config
