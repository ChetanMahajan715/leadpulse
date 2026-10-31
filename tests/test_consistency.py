from leadpulse.models import LeadInput
from leadpulse.scoring import score_lead
from tests.cases import ALL, SAMPLE


def test_same_lead_100_times_gives_identical_results():
    for lead in ALL.values():
        first = score_lead(lead).model_dump()
        assert all(score_lead(lead).model_dump() == first for _ in range(100))


def test_formatting_noise_does_not_change_the_score_or_hash():
    noisy = LeadInput(**{k: f"  {v.upper()}  " for k, v in SAMPLE.model_dump().items()})
    noisy.website = "https://www.abctechnologies.com/"
    a, b = score_lead(SAMPLE), score_lead(noisy)
    assert (a.score, a.classification, a.input_hash) == (b.score, b.classification, b.input_hash)
