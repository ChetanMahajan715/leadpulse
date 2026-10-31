from leadpulse.models import LeadInput
from leadpulse.normalize import normalize_lead
from leadpulse.quality import check_quality

PLACEHOLDER = "Placeholder or disposable email domain"
MISMATCH = "Email domain does not match website"


def _check(**fields):
    return check_quality(normalize_lead(LeadInput(**fields)))


def test_sample_lead_catches_placeholder_and_mismatch():
    report = _check(email="rahul@example.com", website="www.abctechnologies.com", phone="+91 9876543210")
    assert report.flags == [PLACEHOLDER, MISMATCH]
    assert report.email_valid and not report.business_email and not report.domain_match
    assert report.phone_valid


def test_clean_business_contact_has_no_flags():
    report = _check(email="rahul@abctechnologies.com", website="abctechnologies.com", phone="9876543210")
    assert report.flags == []
    assert report.business_email and report.domain_match and report.phone_valid


def test_subdomain_email_matches_website():
    assert _check(email="a@mail.abc.com", website="abc.com").domain_match


def test_free_email_is_flagged():
    assert "Free email provider" in _check(email="someone@gmail.com").flags


def test_invalid_email_phone_and_website_are_flagged():
    report = _check(email="not an email", phone="12345", website="hello world")
    assert report.flags == ["Invalid email format", "Invalid phone number", "Invalid website"]


def test_missing_values_are_not_flagged():
    # Missing data is handled by the missing-field rule, not as a quality flag.
    assert _check().flags == []
