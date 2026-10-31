"""Weighted rule engine. Pure and deterministic: no randomness, no clock, no LLM."""

from typing import Any

from leadpulse.actions import next_action, quality_label
from leadpulse.config_loader import load_config
from leadpulse.confidence import compute_confidence
from leadpulse.intent import score_intent
from leadpulse.models import FIELD_LABELS, Classification, FactorResult, LeadInput, ScoreResult
from leadpulse.normalize import contains_any, input_hash, normalize_lead, parse_company_size
from leadpulse.quality import QualityReport, check_quality

# Fields that feed no weighted parameter but still count as missing information.
_UNSCORED_FIELDS = ("name", "company", "website")


def _match_tiers(value: str, raw: str, rules: dict[str, Any]) -> tuple[int, str, bool]:
    """First tier whose keywords appear in value wins. Returns (points, reason, recognised)."""
    for tier in rules["tiers"]:
        if contains_any(value, tier["keywords"]):
            return tier["points"], f"'{raw}' counts as {tier['name']}", True
    return rules["unrecognised_points"], f"'{raw}' not recognised, default points", False


def _company_size(value: str, raw: str, rules: dict[str, Any]) -> tuple[int, str, bool]:
    size = parse_company_size(value)
    if size is None:
        return rules["unrecognised_points"], f"Could not read company size '{raw}', default points", False
    for bucket in rules["buckets"]:
        if bucket["upper"] is None or size <= bucket["upper"]:
            return bucket["points"], f"About {size:g} employees, {bucket['name']} band", True
    raise AssertionError("the last size bucket must have upper: null")


def _contact(report: QualityReport, lead: dict[str, str], rules: dict[str, Any]) -> tuple[int, str]:
    checks = {
        "valid_email": report.email_valid,
        "business_email": report.business_email,
        "domain_match": report.domain_match,
        "valid_phone": report.phone_valid,
    }
    points = sum(rules["checks"][name] for name, ok in checks.items() if ok)
    passed = [name.replace("_", " ") for name, ok in checks.items() if ok] or ["none"]
    failed = [name.replace("_", " ") for name, ok in checks.items() if not ok] or ["none"]
    notes = [f"{FIELD_LABELS[f]} not provided" for f in ("email", "phone") if not lead[f]]
    return points, "; ".join([f"Passed: {', '.join(passed)}", f"failed: {', '.join(failed)}", *notes])


def classify(score: int) -> Classification:
    """Hot / Warm / Cold from the thresholds in the config."""
    thresholds = load_config()["classification"]
    return "Hot" if score >= thresholds["hot"] else "Warm" if score >= thresholds["warm"] else "Cold"


def score_lead(lead: LeadInput) -> ScoreResult:
    """Score a lead with the weighted rules and return every rule-based output."""
    config = load_config()
    normalized = normalize_lead(lead)
    report = check_quality(normalized)
    missing = [field for field, value in normalized.items() if not value]
    unrecognised: list[str] = []
    factors: list[FactorResult] = []

    for key, rules in config["parameters"].items():
        if key == "contact_quality":
            points, reason = _contact(report, normalized, rules)
        elif not normalized[rules["field"]]:
            points = int(rules["max"] * config["missing_neutral_ratio"])
            reason = f"{FIELD_LABELS[rules['field']]} not provided, neutral {points} of {rules['max']}"
        else:
            value, raw = normalized[rules["field"]], getattr(lead, rules["field"]).strip()
            if key == "buying_intent":
                (points, reason), recognised = score_intent(value), True
            elif key == "company_size":
                points, reason, recognised = _company_size(value, raw, rules)
            else:
                points, reason, recognised = _match_tiers(value, raw, rules)
            if not recognised and rules.get("flag_unrecognised", True):
                unrecognised.append(FIELD_LABELS[rules["field"]])
        factors.append(FactorResult(
            key=key, label=rules["label"], points=points, max_points=rules["max"], reason=reason,
            positive=points >= rules["max"] * config["positive_ratio"],
        ))

    score = sum(f.points for f in factors)
    classification = classify(score)
    confidence, confidence_label = compute_confidence(missing, len(unrecognised), len(report.flags))
    lines = {f.key: f"{f.label} {f.points}/{f.max_points}: {f.reason}" for f in factors}
    return ScoreResult(
        score=score,
        classification=classification,
        confidence=confidence,
        confidence_label=confidence_label,
        quality_label=quality_label(classification, confidence, confidence_label),
        next_action=next_action(classification, report.flags),
        factors=factors,
        positive_factors=[lines[f.key] for f in factors if f.positive],
        negative_factors=[lines[f.key] for f in factors if not f.positive]
        + [f"{FIELD_LABELS[f]} not provided" for f in _UNSCORED_FIELDS if f in missing],
        flags=report.flags,
        missing_fields=[FIELD_LABELS[f] for f in missing],
        unrecognised=unrecognised,
        scoring_version=config["scoring_version"],
        input_hash=input_hash(normalized),
    )


def compare_factors(before: ScoreResult, after: ScoreResult) -> list[tuple[str, int, int]]:
    """(label, old points, new points) for every factor that changed (What-If Simulator)."""
    return [(a.label, a.points, b.points) for a, b in zip(before.factors, after.factors) if a.points != b.points]
