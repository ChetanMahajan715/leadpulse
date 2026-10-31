"""Data-quality checks on email, phone and website (feed both scoring and confidence)."""

import re
from dataclasses import dataclass, field

import phonenumbers

from leadpulse.config_loader import load_config
from leadpulse.normalize import email_domain, website_domain

_EMAIL = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$")
_DOMAIN = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}$")


@dataclass
class QualityReport:
    """Result of the contact checks. Missing values are not flagged here."""

    email_valid: bool = False
    business_email: bool = False
    domain_match: bool = False
    phone_valid: bool = False
    website_valid: bool = False
    flags: list[str] = field(default_factory=list)


def _phone_is_valid(phone: str, region: str) -> bool:
    try:
        return phonenumbers.is_valid_number(phonenumbers.parse(phone, region))
    except phonenumbers.NumberParseException:
        return False


def _same_domain(a: str, b: str) -> bool:
    return a == b or a.endswith("." + b) or b.endswith("." + a)


def check_quality(lead: dict[str, str]) -> QualityReport:
    """Run every data-quality check on a normalised lead."""
    rules = load_config()["data_quality"]
    report = QualityReport()
    site = website_domain(lead["website"])
    report.website_valid = bool(_DOMAIN.match(site))

    if lead["email"]:
        domain = email_domain(lead["email"])
        report.email_valid = bool(_EMAIL.match(lead["email"]))
        if not report.email_valid:
            report.flags.append("Invalid email format")
        elif domain in rules["placeholder_email_domains"]:
            report.flags.append("Placeholder or disposable email domain")
        elif domain in rules["free_email_domains"]:
            report.flags.append("Free email provider")
        else:
            report.business_email = True

        if report.email_valid and report.website_valid:
            report.domain_match = _same_domain(domain, site)
            if not report.domain_match:
                report.flags.append("Email domain does not match website")

    if lead["phone"]:
        report.phone_valid = _phone_is_valid(lead["phone"], rules["phone_region"])
        if not report.phone_valid:
            report.flags.append("Invalid phone number")

    if lead["website"] and not report.website_valid:
        report.flags.append("Invalid website")
    return report
