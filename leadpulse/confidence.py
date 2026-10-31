"""Confidence: how sure the system is about its own score (separate from the score)."""

from leadpulse.config_loader import load_config


def compute_confidence(missing_fields: list[str], unrecognised: int, flags: int) -> tuple[int, str]:
    """Start at 100 and subtract per missing field, fallback value and quality flag.

    Missing Job Title / Requirement / Company Size, and Email+Phone both missing, are critical.
    Returns (percent 0-100, "High" | "Medium" | "Low").
    """
    rules = load_config()["confidence"]
    missing = set(missing_fields)
    critical = len(missing & set(rules["critical_fields"]))
    if {"email", "phone"} <= missing:
        critical += 1
        missing -= {"email", "phone"}
    other = len(missing) - len(missing & set(rules["critical_fields"]))

    value = (rules["start"] - critical * rules["missing_critical"] - other * rules["missing_other"]
             - unrecognised * rules["unrecognised"] - flags * rules["flag"])
    value = max(0, min(100, value))
    labels = rules["labels"]
    label = "High" if value >= labels["high"] else "Medium" if value >= labels["medium"] else "Low"
    return value, label
