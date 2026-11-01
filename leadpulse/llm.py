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

_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
_ONES = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9}
_TEENS = {"ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
          "seventeen": 17, "eighteen": 18, "nineteen": 19}
_TENS_WORDS = re.compile(rf"\b({'|'.join(_TENS)})(?:[\s-]+({'|'.join(_ONES)}))?\b")
# Standalone "one" is left alone: "one of the best" is not a number claim.
_SMALL_WORDS = re.compile(rf"\b({'|'.join([*_TEENS, *(w for w in _ONES if w != 'one')])})\b")
_HUNDRED = re.compile(r"\b(?:(?:a|one)\s+)?hundred\b")

_OUT_OF_100 = re.compile(r"\b(\d{1,3})\s*(?:/|out of|of)\s*100\b")
_SCORE_MENTIONS = (
    _OUT_OF_100,
    # "score of 72", "rated 72", "Score: 72". "15 of 25" is a factor, and "confidence score" is not the score.
    re.compile(r"(?<!confidence )\b(?:scor(?:e|es|ed|ing)|rating|rated|grade[ds]?)\b"
               r"(?:[\s:=]+(?:of|is|was|at|to|about|around|roughly|approximately|just|only|a|an|stands|sits|comes"
               r"|came|in|reached|overall|now))*[\s:=]+(\d{1,3})\b(?!\s*(?:/|of|out of)\s*(?!100\b)\d)"),
    re.compile(r"\b(\d{1,3})[\s-]*(?:points?|pts)\s+(?:overall|in total|total)\b"),
    re.compile(r"\b(?:overall|total|final)\s+(?:of\s+)?(\d{1,3})\b"),
    re.compile(r"\b(\d{1,3})(?:%|[\s-]*point)?[\s-]*(?:lead|prospect|score|rating)\b"),
)
_CLASS_MENTIONS = (
    re.compile(r"\b(hot|warm|cold)[\s-]+(?:lead|prospect|opportunity|score|rating|class|classification|category|tier)\b"),
    re.compile(r"\b(?:classif\w+|categori[sz]\w+|labell?ed|rated|marked|class|lead|prospect)"
               r"(?:\s+(?:is|as|was|of|a))*[\s:]+[\"']?(hot|warm|cold)\b(?!\s+(?:outreach|call|calling|email|list))"),
)


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


def _words_to_digits(text: str) -> str:
    """Rewrite spelled-out numbers ('seventy-two', 'a hundred') as digits."""
    text = _HUNDRED.sub("100", text)
    text = _TENS_WORDS.sub(lambda m: str(_TENS[m[1]] + _ONES.get(m[2], 0)), text)
    return _SMALL_WORDS.sub(lambda m: str(_TEENS.get(m[1]) or _ONES[m[1]]), text)


def contradicts_result(text: str, result: ScoreResult, context: str) -> bool:
    """True if text states a score or Hot/Warm/Cold class different from the computed one.

    context is the prompt the LLM was given. As a catch-all for wordings the patterns miss, a number
    too large to be one factor's points must come from that context.
    Limit: these are English patterns, so a paraphrase below that size can still slip; the prompt forbids it too.
    """
    text = _words_to_digits(text.lower())
    scores = {int(m) for pattern in _SCORE_MENTIONS for m in pattern.findall(text)}
    classes = {m.capitalize() for pattern in _CLASS_MENTIONS for m in pattern.findall(text)}
    if scores - {result.score} or classes - {result.classification}:
        return True
    largest_factor = max(f.max_points for f in result.factors)
    known = {int(n) for n in re.findall(r"\d+", context)} | {result.score, result.confidence}
    numbers = {int(n) for n in re.findall(r"\d+", _OUT_OF_100.sub("", text))}
    return any(largest_factor < n <= 100 and n not in known for n in numbers)


def _is_acceptable(insights: LLMInsights, result: ScoreResult, context: str) -> bool:
    text = f"{insights.explanation} {insights.quality_note} {insights.next_action}"
    return not contradicts_result(text, result, context)


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
    user = build_user_prompt(lead, result)
    cached = cache.get(key)
    if cached is not None:
        try:
            insights = LLMInsights.model_validate(cached)
        except ValidationError:
            insights = None  # corrupt entry: ask the LLM again
        if insights is not None and _is_acceptable(insights, result, user):
            return insights

    for _ in range(2):  # one retry on invalid JSON
        try:
            insights = LLMInsights.model_validate_json(call(SYSTEM_PROMPT, user, settings))
        except ValidationError:
            continue
        except Exception:  # network, auth, quota, timeout: the app must keep working offline
            break
        if not _is_acceptable(insights, result, user):
            break
        insights = insights.model_copy(update={"source": "llm"})
        cache.put(key, insights.model_dump())
        return insights
    return template_insights(lead, result)
