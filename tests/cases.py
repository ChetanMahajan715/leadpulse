"""Sample leads shared by the tests (documented in docs/TEST_CASES.md)."""

from leadpulse.models import SAMPLE_LEAD_FIELDS, LeadInput

SAMPLE = LeadInput(**SAMPLE_LEAD_FIELDS)

WARM = LeadInput(
    name="Priya Nair", company="BrightAds", website="brightads.in", job_title="Marketing Manager",
    industry="Marketing Agency", location="Pune", company_size="20", lead_source="LinkedIn",
    requirement="need a tool to manage leads", email="priya@brightads.in", phone="+91 9123456780",
)

COLD = LeadInput(
    name="Amit Kumar", company="Small Shop", website="smallshop.in", job_title="Intern",
    industry="Agriculture", location="Patna", company_size="5", lead_source="Cold outreach",
    requirement="just browsing", email="amit123@gmail.com", phone="9876501234",
)

MISSING = LeadInput(name="Neha Gupta", email="neha@nehadesigns.com")

JUNK = LeadInput(
    name="asdf", website="not a site", job_title="xyzzy", requirement="asdfgh",
    email="asdf@@", phone="123",
)

INTERNATIONAL = LeadInput(
    name="James Carter", company="Acme Ltd", website="https://acme.co.uk", job_title="Head of Sales",
    industry="SaaS", location="London, UK", company_size="250", lead_source="Referral",
    requirement="Need a CRM demo for our sales team asap", email="james@acme.co.uk",
    phone="+44 20 7946 0958",
)

ALL = {"sample": SAMPLE, "warm": WARM, "cold": COLD, "missing": MISSING, "junk": JUNK,
       "international": INTERNATIONAL}
