"""Buying-intent signals from the free-text Requirement field."""

from leadpulse.config_loader import load_config
from leadpulse.normalize import contains_any


def score_intent(requirement: str) -> tuple[int, str]:
    """Score a non-empty, normalised requirement. Returns (points, reason)."""
    rules = load_config()["parameters"]["buying_intent"]
    hits = {name: contains_any(requirement, signal["keywords"]) for name, signal in rules["signals"].items()}

    if not any(hits.values()) and len(requirement.split()) < rules["short_text_words"]:
        return rules["short_text_points"], "Requirement is too vague to show intent"

    points = rules["base"] + sum(rules["signals"][name]["points"] for name, found in hits.items() if found)
    points = min(points, rules["max"])
    signals = [f"{name} ({', '.join(found)})" for name, found in hits.items() if found]
    reason = "Signals: " + "; ".join(signals) if signals else "Requirement given but no clear buying signal"
    return points, reason
