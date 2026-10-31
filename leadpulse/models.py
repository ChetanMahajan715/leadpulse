"""Pydantic data models shared by the engine, the LLM layer and the UI."""

import math
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

MAX_FIELD_CHARS = 1000

# Internal field name -> human label (also the CSV column names).
FIELD_LABELS: dict[str, str] = {
    "name": "Name",
    "company": "Company Name",
    "website": "Website",
    "job_title": "Job Title",
    "industry": "Industry",
    "location": "Company Location",
    "company_size": "Company Size",
    "lead_source": "Lead Source",
    "requirement": "Requirement",
    "email": "Email",
    "phone": "Phone",
}

Classification = Literal["Hot", "Warm", "Cold"]

# The sample lead from the brief (also the UI's "Load sample lead").
SAMPLE_LEAD_FIELDS: dict[str, str] = {
    "name": "Rahul Sharma",
    "company": "ABC Technologies",
    "website": "www.abctechnologies.com",
    "job_title": "Founder",
    "industry": "IT Services",
    "location": "Bangalore",
    "company_size": "50–100 Employees",
    "lead_source": "Website",
    "requirement": "Looking for CRM software",
    "email": "rahul@example.com",
    "phone": "+91 9876543210",
}


class LeadInput(BaseModel):
    """Raw lead as typed by a user or read from a CSV row. Every field is optional."""

    name: str = ""
    company: str = ""
    website: str = ""
    job_title: str = ""
    industry: str = ""
    location: str = ""
    company_size: str = ""
    lead_source: str = ""
    requirement: str = ""
    email: str = ""
    phone: str = ""

    @field_validator("*", mode="before")
    @classmethod
    def _to_text(cls, value: Any) -> str:
        """Coerce None / NaN / numbers to text and cap the length (CSV cells can be anything)."""
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return ""
        return str(value)[:MAX_FIELD_CHARS]


class FactorResult(BaseModel):
    """Points earned by one scoring parameter, with the reason."""

    key: str
    label: str
    points: int
    max_points: int
    reason: str
    positive: bool


class ScoreResult(BaseModel):
    """Everything the rule engine decides about a lead. Produced without any LLM."""

    score: int = Field(ge=0, le=100)
    classification: Classification
    confidence: int = Field(ge=0, le=100)
    confidence_label: Literal["High", "Medium", "Low"]
    quality_label: str
    next_action: str
    factors: list[FactorResult]
    positive_factors: list[str]
    negative_factors: list[str]
    flags: list[str]
    missing_fields: list[str]
    unrecognised: list[str]
    scoring_version: str
    input_hash: str


class FollowUpEmail(BaseModel):
    """Draft first-contact email."""

    subject: str
    body: str


class LLMInsights(BaseModel):
    """Strict JSON contract for the LLM response (also used for offline templates)."""

    explanation: str
    quality_note: str
    next_action: str
    follow_up_email: FollowUpEmail
    source: Literal["llm", "template"] = "llm"
