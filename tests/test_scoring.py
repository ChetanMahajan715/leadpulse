import pytest

from leadpulse.models import LeadInput
from leadpulse.scoring import compare_factors, score_lead
from tests.cases import ALL, COLD, INTERNATIONAL, JUNK, MISSING, SAMPLE, WARM


def _points(result) -> dict[str, int]:
    return {f.key: f.points for f in result.factors}


def test_sample_lead_matches_the_brief():
    r = score_lead(SAMPLE)
    assert _points(r) == {
        "decision_authority": 20, "buying_intent": 15, "company_size": 15, "industry_fit": 10,
        "lead_source": 9, "contact_quality": 5, "location_fit": 10,
    }
    assert (r.score, r.classification, r.confidence, r.confidence_label) == (84, "Hot", 90, "High")
    assert r.flags == ["Placeholder or disposable email domain", "Email domain does not match website"]
    assert r.quality_label == "Sales-ready, high-quality lead"
    assert r.next_action.startswith("Verify contact details (placeholder or disposable email domain")
    assert r.next_action.endswith("then call within 24 hours and offer a product demo")
    assert r.scoring_version == "1.0.0"


def test_strong_warm_lead():
    r = score_lead(WARM)
    assert (r.score, r.classification, r.confidence_label) == (73, "Warm", "High")
    assert r.quality_label == "Promising lead, needs nurturing"
    assert r.flags == []


def test_cold_lead():
    r = score_lead(COLD)
    assert (r.score, r.classification) == (29, "Cold")
    assert "Free email provider" in r.flags
    assert r.next_action.endswith("add to a nurture email campaign; re-evaluate in 30 days")


def test_missing_data_lead_gets_neutral_points_and_low_confidence():
    r = score_lead(MISSING)
    pts = _points(r)
    assert pts["decision_authority"] == 6 and pts["buying_intent"] == 7 and pts["company_size"] == 4
    assert pts["contact_quality"] == 5      # valid + business email, no phone, no website to match
    assert (r.score, r.classification, r.confidence, r.confidence_label) == (31, "Cold", 0, "Low")
    assert r.quality_label == "Insufficient data to judge"
    assert any("Job Title not provided" in n for n in r.negative_factors)


def test_junk_lead_is_flagged_with_low_confidence():
    r = score_lead(JUNK)
    assert r.flags == ["Invalid email format", "Invalid phone number", "Invalid website"]
    assert "Job Title" in r.unrecognised
    assert r.confidence_label == "Low"
    assert r.classification == "Cold"


def test_international_lead():
    r = score_lead(INTERNATIONAL)
    assert _points(r)["location_fit"] == 6
    assert _points(r)["buying_intent"] == 22
    assert (r.score, r.classification) == (87, "Hot")


def test_empty_lead_does_not_crash():
    r = score_lead(LeadInput())
    assert r.classification == "Cold" and r.confidence == 0


@pytest.mark.parametrize("lead", list(ALL.values()) + [LeadInput(), LeadInput(requirement="x" * 5000)])
def test_score_and_factor_bounds(lead):
    r = score_lead(lead)
    assert 0 <= r.score <= 100
    assert r.score == sum(f.points for f in r.factors)
    for f in r.factors:
        assert 0 <= f.points <= f.max_points


@pytest.mark.parametrize("title, points", [
    ("Co-Founder", 20), ("Managing Director", 20), ("Vice President, Sales", 17), ("Sales Head", 17),
    ("Team Lead", 12), ("Senior Analyst", 7), ("Engineering Intern", 3), ("Wizard", 7),
])
def test_job_title_tiers(title, points):
    assert _points(score_lead(LeadInput(job_title=title)))["decision_authority"] == points


def test_compare_factors_reports_changes_only():
    before = score_lead(SAMPLE)
    after = score_lead(SAMPLE.model_copy(update={"job_title": "Intern"}))
    assert compare_factors(before, after) == [("Decision authority", 20, 3)]
