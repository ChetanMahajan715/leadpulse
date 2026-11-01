import json

import pytest

from leadpulse import cache, llm
from leadpulse.prompts import PROMPT_VERSION, build_user_prompt
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


@pytest.mark.parametrize("bad", [
    # Found by independent QA: all of these were accepted for a lead scored 84 Hot.
    "This lead has a rating of 72.",
    "It earned 72 points overall.",
    "We put it at seventy-two out of a hundred.",
    "This Warm prospect needs nurturing.",
    # Close variants of the same mistakes.
    "It is rated 72.",
    "A 72-point lead.",
    "Overall it comes in at a solid 72.",
    "The final score stands at 72.",
    "A score of eighty one fits this lead.",
    "It earned 20 points in total.",
    "Score: 72.",
    "The lead is warm.",
    "It was classified as cold.",
    "Classification: Warm.",
])
def test_guardrail_rejects_other_wordings_of_a_wrong_score_or_class(bad):
    fake = FakeLLM(json.dumps({**GOOD, "explanation": bad}))
    assert llm.generate_insights(SAMPLE, score_lead(SAMPLE), call=fake).source == "template"


@pytest.mark.parametrize("field", ["quality_note", "next_action"])
def test_guardrail_also_covers_the_other_text_fields(field):
    fake = FakeLLM(json.dumps({**GOOD, field: "This is a 72 out of 100 lead."}))
    assert llm.generate_insights(SAMPLE, score_lead(SAMPLE), call=fake).source == "template"


@pytest.mark.parametrize("good", [
    "It scored 84/100: decision authority earned 20 of 20 and confidence is 90%.",
    "Buying intent scored 15 of 25 and company size 15 of 15.",
    "The confidence score of 90 reflects two data-quality flags.",
    "It has a score of eighty-four, which is a Hot lead.",
    "ABC Technologies has 50-100 employees, midpoint 75, and came from a website form.",
    "Verify the email, then call within 24 hours.",
    "Unlike a cold outreach contact, this lead came through the website.",
    "It scores well on 7 parameters overall.",
    # Real Gemini output for this lead, saved from a live run.
    "Rahul Sharma received a strong hot score of 84 due to his top-level decision-making authority "
    "as Founder of ABC Technologies, a high-fit IT Services company of 50-100 employees in Bangalore.",
])
def test_guardrail_keeps_answers_that_do_not_contradict(good):
    fake = FakeLLM(json.dumps({**GOOD, "explanation": good}))
    assert llm.generate_insights(SAMPLE, score_lead(SAMPLE), call=fake).source == "llm"


def test_a_number_typed_in_the_lead_does_not_excuse_a_wrong_score():
    lead = SAMPLE.model_copy(update={"requirement": "CRM software for 72 users"})
    result = score_lead(lead)
    fake = FakeLLM(json.dumps({**GOOD, "explanation": f"It serves 72 users and scored {result.score}."}))
    assert llm.generate_insights(lead, result, call=fake).source == "llm"
    wrong = FakeLLM(json.dumps({**GOOD, "explanation": "This lead has a rating of 72."}))
    other = lead.model_copy(update={"name": "Different Person"})
    assert llm.generate_insights(other, score_lead(other), call=wrong).source == "template"


def test_template_text_never_trips_the_guardrail():
    for lead in (SAMPLE, MISSING):
        result = score_lead(lead)
        insights = llm.template_insights(lead, result)
        text = f"{insights.explanation} {insights.quality_note} {insights.next_action}"
        assert not llm.contradicts_result(text, result, build_user_prompt(lead, result))


def test_cached_answer_that_breaks_the_guardrail_is_not_served():
    result = score_lead(SAMPLE)
    key = cache.cache_key(result.input_hash, result.scoring_version, PROMPT_VERSION, llm.llm_settings()[2])
    cache.put(key, {**GOOD, "explanation": "This lead has a rating of 72.", "source": "llm"})
    assert llm.generate_insights(SAMPLE, result, call=FakeLLM(TimeoutError())).source == "template"


def test_corrupt_cache_entry_does_not_crash():
    result = score_lead(SAMPLE)
    key = cache.cache_key(result.input_hash, result.scoring_version, PROMPT_VERSION, llm.llm_settings()[2])
    cache.put(key, {"explanation": 1})
    assert llm.generate_insights(SAMPLE, result, call=FakeLLM(TimeoutError())).source == "template"


def test_same_lead_twice_hits_the_cache():
    fake = FakeLLM(json.dumps(GOOD))
    first = llm.generate_insights(SAMPLE, score_lead(SAMPLE), call=fake)
    second = llm.generate_insights(SAMPLE, score_lead(SAMPLE), call=fake)
    assert first == second and fake.calls == 1
