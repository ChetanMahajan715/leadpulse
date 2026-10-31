"""Prompts for the LLM explainer. Bump PROMPT_VERSION whenever a prompt changes (it keys the cache)."""

import json

from leadpulse.models import LeadInput, ScoreResult

PROMPT_VERSION = "1.0"

SYSTEM_PROMPT = """You are a B2B sales analyst. A rule-based engine has already scored a sales lead.
Your job is only to explain that result and draft a first-contact email.

Rules:
- Explain the given score using only the given factors, flags and lead data.
- Never invent facts about the company or the person.
- Never output or suggest a different score or a different Hot/Warm/Cold class.
- Keep the recommended next action consistent with the given base action; you may only personalise its wording.
- Be concise, professional, plain English. No markdown.
- The seller offers CRM and sales-automation software to SMB and mid-market companies.

Reply with a single JSON object with exactly these keys:
{"explanation": "3-4 sentences on why the score is what it is",
 "quality_note": "one sentence adding context to the quality label",
 "next_action": "the base action, personalised in one or two sentences",
 "follow_up_email": {"subject": "short subject line", "body": "a short, friendly email under 120 words, signed [Your name]"}}"""


def build_user_prompt(lead: LeadInput, result: ScoreResult) -> str:
    """Serialise the lead and the full rule-based result for the LLM."""
    payload = {
        "lead": {k: " ".join(v.split()) for k, v in lead.model_dump().items()},
        "score": result.score,
        "classification": result.classification,
        "confidence": f"{result.confidence}% ({result.confidence_label})",
        "quality_label": result.quality_label,
        "base_next_action": result.next_action,
        "factors": [
            {"parameter": f.label, "points": f.points, "max": f.max_points, "reason": f.reason}
            for f in result.factors
        ],
        "data_quality_flags": result.flags,
        "missing_fields": result.missing_fields,
    }
    return "Explain this scored lead and return the JSON object.\n\n" + json.dumps(payload, ensure_ascii=False, indent=1)
