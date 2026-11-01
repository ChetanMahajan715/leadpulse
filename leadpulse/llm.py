"""LLM explainer: provider client, strict JSON validation, guardrail, cache and offline templates.

The LLM never produces the score. It only explains a ScoreResult that the rule engine already built.
"""

import os
import re
from collections.abc import Callable

from dotenv import load_dotenv
from pydantic import ValidationError

from leadpulse import cache
from leadpulse.models import FollowUpEmail, LeadInput, LLMInsights, ScoreResult
from leadpulse.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt

load_dotenv()

# Flash-Lite: fast, generous free tier and less often overloaded than Flash; enough for short explanations.
DEFAULT_MODELS = {"gemini": "gemini-flash-lite-latest", "groq": "openai/gpt-oss-20b"}
PROVIDER_NAMES = {"gemini": "Gemini", "groq": "Groq"}
TIMEOUT_SECONDS = 20

Settings = tuple[str, str, str]  # (provider, api_key, model)
LLMCall = Callable[[str, str, Settings], str]

_SCORE_MENTIONS = (
    re.compile(r"\bscor\w*\s+(?:of\s+|is\s+|was\s+|at\s+)?(\d{1,3})\b", re.IGNORECASE),
    re.compile(r"\b(\d{1,3})\s*(?:/|out of)\s*100\b", re.IGNORECASE),
)
_CLASS_MENTION = re.compile(r"\b(hot|warm|cold)\s+lead", re.IGNORECASE)


def llm_settings() -> Settings | None:
    """Provider, key and model from the environment, or None when offline."""
    provider = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
    key = os.getenv(f"{provider.upper()}_API_KEY", "").strip()
    if provider not in DEFAULT_MODELS or not key:
        return None
    return provider, key, os.getenv("LLM_MODEL", "").strip() or DEFAULT_MODELS[provider]


def llm_status() -> str | None:
    """Display name of the active provider, or None in offline mode."""
    settings = llm_settings()
    return PROVIDER_NAMES[settings[0]] if settings else None


def call_llm(system: str, user: str, settings: Settings) -> str:
    """Send one request to the configured provider and return the raw JSON text."""
    provider, key, model = settings
    if provider == "gemini":
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=TIMEOUT_SECONDS * 1000))
        response = client.models.generate_content(
            model=model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system, temperature=0, response_mime_type="application/json",
            ),
        )
        return response.text or ""

    from groq import Groq

    client = Groq(api_key=key, timeout=TIMEOUT_SECONDS, max_retries=0)
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return response.choices[0].message.content or ""


def contradicts_result(text: str, result: ScoreResult) -> bool:
    """True if text states a score or Hot/Warm/Cold class different from the computed one."""
    scores = {int(m) for pattern in _SCORE_MENTIONS for m in pattern.findall(text)}
    classes = {m.capitalize() for m in _CLASS_MENTION.findall(text)}
    return bool(scores - {result.score}) or bool(classes - {result.classification})


def template_insights(lead: LeadInput, result: ScoreResult) -> LLMInsights:
    """Deterministic, rule-based explanation and email used when the LLM is off or fails."""
    strong = [f.label.lower() for f in sorted(result.factors, key=lambda f: f.points / f.max_points, reverse=True)
              if f.positive][:3]
    weak = [f.label.lower() for f in result.factors if not f.positive][:3]
    held_back = []
    if result.flags:
        held_back.append(f"{len(result.flags)} data-quality flag(s)")
    if result.missing_fields:
        held_back.append(f"{len(result.missing_fields)} missing field(s)")

    explanation = f"This lead scored {result.score}/100 and is classified {result.classification}."
    if strong:
        explanation += f" It scores well on {', '.join(strong)}."
    if weak:
        explanation += f" Points were lost on {', '.join(weak)}."
    explanation += f" Confidence is {result.confidence}% ({result.confidence_label})"
    explanation += f", reduced by {' and '.join(held_back)}." if held_back else "."

    first_name = lead.name.split()[0] if lead.name.split() else "there"
    need = " ".join(lead.requirement.split()).rstrip(".")
    about = f" about: \"{need}\"" if need else ""
    closing = {
        "Hot": "Would you have 20 minutes this week for a short demo tailored to your team?",
        "Warm": "I would be happy to share a short case study from a team similar to yours. "
                "Would that be useful?",
        "Cold": "I will share a few resources on how teams like yours manage leads. "
                "Feel free to reply whenever the timing is right.",
    }[result.classification]
    company = lead.company.strip()
    body = (f"Hi {first_name},\n\nThank you for getting in touch{about}. "
            f"Our CRM and sales-automation platform helps {company or 'growing teams'} capture, "
            f"prioritise and follow up on leads in one place.\n\n{closing}\n\nBest regards,\n[Your name]")
    subject = f"Following up on your enquiry{f' for {company}' if company else ''}"
    return LLMInsights(
        explanation=explanation,
        quality_note=result.quality_label + ".",
        next_action=result.next_action,
        follow_up_email=FollowUpEmail(subject=subject, body=body),
        source="template",
    )


def generate_insights(lead: LeadInput, result: ScoreResult, call: LLMCall = call_llm) -> LLMInsights:
    """LLM explanation for a scored lead, cached; falls back to templates on any problem."""
    settings = llm_settings()
    if settings is None:
        return template_insights(lead, result)

    key = cache.cache_key(result.input_hash, result.scoring_version, PROMPT_VERSION, settings[2])
    cached = cache.get(key)
    if cached is not None:
        return LLMInsights.model_validate(cached)

    user = build_user_prompt(lead, result)
    for _ in range(2):  # one retry on invalid JSON
        try:
            insights = LLMInsights.model_validate_json(call(SYSTEM_PROMPT, user, settings))
        except ValidationError:
            continue
        except Exception:  # network, auth, quota, timeout: the app must keep working offline
            break
        if contradicts_result(f"{insights.explanation} {insights.quality_note} {insights.next_action}", result):
            break
        insights = insights.model_copy(update={"source": "llm"})
        cache.put(key, insights.model_dump())
        return insights
    return template_insights(lead, result)
