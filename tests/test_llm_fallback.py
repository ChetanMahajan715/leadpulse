import json

import pytest

from leadpulse import cache, llm
from leadpulse.scoring import score_lead
from tests.cases import MISSING, SAMPLE

GOOD = {
    "explanation": "Rahul is a founder with a clear CRM need, which is why the score is 84.",
    "quality_note": "Strong fit, but the email domain needs checking.",
    "next_action": "Verify the email, then call within 24 hours to offer a demo.",
    "follow_up_email": {"subject": "CRM for ABC Technologies", "body": "Hi Rahul, ..."},
}


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "")


class FakeLLM:
    """Stands in for the real API; returns the queued replies in order."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = 0

    def __call__(self, system: str, user: str, settings: tuple[str, str, str]) -> str:
        self.calls += 1
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def test_no_api_key_uses_templates(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY")
    result = score_lead(SAMPLE)
    insights = llm.generate_insights(SAMPLE, result, call=FakeLLM())
    assert insights.source == "template"
    assert "84" in insights.explanation and "Hot" in insights.explanation
    assert insights.next_action == result.next_action
    assert insights.follow_up_email.subject and "Rahul" in insights.follow_up_email.body
    assert llm.llm_status() is None


def test_template_handles_an_almost_empty_lead(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY")
    insights = llm.generate_insights(MISSING, score_lead(MISSING))
    assert insights.source == "template" and insights.follow_up_email.body


def test_valid_llm_reply_is_used():
    fake = FakeLLM(json.dumps(GOOD))
    insights = llm.generate_insights(SAMPLE, score_lead(SAMPLE), call=fake)
    assert insights.source == "llm"
    assert insights.explanation == GOOD["explanation"]


def test_invalid_json_is_retried_once_then_succeeds():
    fake = FakeLLM("not json", json.dumps(GOOD))
    assert llm.generate_insights(SAMPLE, score_lead(SAMPLE), call=fake).source == "llm"
    assert fake.calls == 2


def test_invalid_json_twice_falls_back_to_template():
    fake = FakeLLM("not json", '{"explanation": 1}')
    assert llm.generate_insights(SAMPLE, score_lead(SAMPLE), call=fake).source == "template"


def test_api_error_falls_back_without_raising():
    fake = FakeLLM(TimeoutError("slow"))
    assert llm.generate_insights(SAMPLE, score_lead(SAMPLE), call=fake).source == "template"
    assert fake.calls == 1


@pytest.mark.parametrize("bad", [
    "The lead scored 72 because of the title.",
    "Overall this is a 60/100 lead.",
    "A score of 90 out of 100 reflects strong fit.",
    "This is a Warm lead overall.",
])
def test_guardrail_rejects_a_different_score_or_class(bad):
    fake = FakeLLM(json.dumps({**GOOD, "explanation": bad}))
    assert llm.generate_insights(SAMPLE, score_lead(SAMPLE), call=fake).source == "template"


def test_guardrail_allows_factor_points_and_confidence():
    text = "It scored 84/100: decision authority earned 20 of 20 and confidence is 90%."
    fake = FakeLLM(json.dumps({**GOOD, "explanation": text}))
    assert llm.generate_insights(SAMPLE, score_lead(SAMPLE), call=fake).source == "llm"


def test_same_lead_twice_hits_the_cache():
    fake = FakeLLM(json.dumps(GOOD))
    first = llm.generate_insights(SAMPLE, score_lead(SAMPLE), call=fake)
    second = llm.generate_insights(SAMPLE, score_lead(SAMPLE), call=fake)
    assert first == second and fake.calls == 1
