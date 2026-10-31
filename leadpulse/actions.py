"""Rule-based quality label and recommended next action."""

from leadpulse.config_loader import load_config


def quality_label(classification: str, confidence: int, confidence_label: str) -> str:
    """Map class + confidence to the quality assessment label."""
    labels = load_config()["quality_labels"]
    if confidence < labels["insufficient_below"]:
        return labels["insufficient"]
    if classification == "Hot":
        return labels["hot_low_confidence"] if confidence_label == "Low" else labels["hot_confident"]
    return labels["warm"] if classification == "Warm" else labels["cold"]


def next_action(classification: str, flags: list[str]) -> str:
    """Base action for the class, prefixed with a verification step when data flags exist."""
    actions = load_config()["next_actions"]
    base = actions[classification]
    if not flags:
        return base
    issues = ", ".join(flag.lower() for flag in flags)
    return f"{actions['verify_prefix']} ({issues}), then {base[0].lower()}{base[1:]}"
