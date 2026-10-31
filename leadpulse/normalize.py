"""Input cleaning: text normalisation, domain extraction, company-size parsing, hashing."""

import hashlib
import json
import re

from leadpulse.models import LeadInput

_URL_PREFIX = re.compile(r"^(https?://)?(www\.)?")
_NUMBER = re.compile(r"\d+")


def clean(text: str) -> str:
    """Trim, lowercase and collapse internal whitespace."""
    return " ".join(text.split()).lower()


def strip_url(text: str) -> str:
    """Clean a URL and remove the scheme, a leading www. and any trailing slash."""
    return _URL_PREFIX.sub("", clean(text)).rstrip("/")


def website_domain(website: str) -> str:
    """Return the bare domain of a website ('https://www.abc.com/x' -> 'abc.com')."""
    return strip_url(website).split("/")[0]


def email_domain(email: str) -> str:
    """Return the part after '@', or '' when there is no single '@'."""
    parts = clean(email).split("@")
    return parts[1] if len(parts) == 2 else ""


def parse_company_size(text: str) -> float | None:
    """Parse '50-100 employees' -> 75, '75' -> 75, '1000+' -> 1001. None if unparseable or 0."""
    numbers = [int(n) for n in _NUMBER.findall(text.replace(",", ""))]
    if not numbers or max(numbers) == 0:
        return None
    if len(numbers) >= 2:
        return (numbers[0] + numbers[1]) / 2
    return float(numbers[0] + 1) if "+" in text else float(numbers[0])


def contains_any(text: str, keywords: list[str]) -> list[str]:
    """Return the keywords found in text, matched on word boundaries (symbols by substring)."""
    found = []
    for keyword in keywords:
        if keyword[0].isalnum():
            if re.search(rf"(?<![\w]){re.escape(keyword)}(?![\w])", text):
                found.append(keyword)
        elif keyword in text:
            found.append(keyword)
    return found


def normalize_lead(lead: LeadInput) -> dict[str, str]:
    """Return the cleaned lead used for matching and hashing."""
    normalized = {field: clean(value) for field, value in lead.model_dump().items()}
    normalized["website"] = strip_url(lead.website)
    return normalized


def input_hash(normalized: dict[str, str]) -> str:
    """SHA-256 of the normalised lead, so identical inputs share one fingerprint."""
    return hashlib.sha256(json.dumps(normalized, sort_keys=True).encode("utf-8")).hexdigest()
