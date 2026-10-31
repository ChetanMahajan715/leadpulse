import pytest

from leadpulse.models import LeadInput
from leadpulse.normalize import (
    clean,
    contains_any,
    email_domain,
    input_hash,
    normalize_lead,
    parse_company_size,
    website_domain,
)


def test_clean_trims_lowercases_and_collapses_spaces():
    assert clean("  Hello   World \n") == "hello world"


def test_website_domain_strips_scheme_www_and_path():
    assert website_domain("https://www.ABCTechnologies.com/about") == "abctechnologies.com"
    assert website_domain("www.abctechnologies.com") == "abctechnologies.com"
    assert website_domain("") == ""


def test_email_domain():
    assert email_domain("Rahul@Example.com ") == "example.com"
    assert email_domain("not-an-email") == ""


@pytest.mark.parametrize(
    "text, expected",
    [
        ("50–100 Employees", 75.0),   # en dash, as in the sample lead
        ("50-100", 75.0),
        ("50-100 employees", 75.0),
        ("75", 75.0),
        ("1000+", 1001.0),            # "N+" means more than N
        ("1,500", 1500.0),
        ("", None),
        ("abc", None),
        ("0", None),
    ],
)
def test_parse_company_size(text, expected):
    assert parse_company_size(text) == expected


def test_contains_any_uses_word_boundaries_and_symbols():
    assert contains_any("need it asap", ["asap", "soon"]) == ["asap"]
    assert contains_any("users and partners", ["rs", "partner"]) == []
    assert contains_any("budget ₹5 lakh", ["₹", "lakh"]) == ["₹", "lakh"]


def test_normalize_and_hash_ignore_formatting_noise():
    a = LeadInput(name=" Rahul  Sharma", website="https://www.abc.com", email="RAHUL@abc.com")
    b = LeadInput(name="rahul sharma", website="abc.com", email="rahul@abc.com ")
    assert normalize_lead(a) == normalize_lead(b)
    assert input_hash(normalize_lead(a)) == input_hash(normalize_lead(b))
    assert len(input_hash(normalize_lead(a))) == 64
