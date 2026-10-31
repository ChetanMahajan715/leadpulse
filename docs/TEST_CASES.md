# Sample Test Cases

Each lead below is defined in [`tests/cases.py`](../tests/cases.py) and checked by the automated tests (`uv run pytest`). The numbers are the engine's real output.

Points order: Authority / Intent / Size / Industry / Source / Contact / Location.

| # | Lead (input summary) | Score | Class | Confidence | Quality | Key reasons |
|---|---|---|---|---|---|---|
| 1 | **Sample lead**: Founder, IT Services, Bangalore, 50–100 employees, Website, "Looking for CRM software", rahul@example.com | **84** | 🔥 Hot | 90% High | Sales-ready, high-quality lead | 20/15/15/10/9/5/10. Founder + CRM need + ideal size. Contact loses 5: example.com is a placeholder and does not match the website (2 flags, -10 confidence). |
| 2 | **Strong warm**: Marketing Manager, Marketing Agency, Pune, 20 employees, LinkedIn, "need a tool to manage leads", matching business email | **73** | 🌤 Warm | 100% High | Promising lead, needs nurturing | 12/15/10/10/6/10/10. Clean data and a clear need, but a manager (not a signer), a small team and a social source keep it just under Hot. |
| 3 | **Cold**: Intern, Agriculture, Patna, 5 employees, Cold outreach, "just browsing", gmail | **29** | ❄️ Cold | 90% High | Low fit / low intent lead | 3/3/5/3/3/5/7. No authority, vague requirement (under 3 words, no keyword), tiny company, cold source. Free email + domain mismatch flagged. |
| 4 | **Missing data**: only Name + Email (neha@nehadesigns.com) | **31** | ❄️ Cold | 0% Low | Insufficient data to judge | 6/7/4/3/3/5/3. Every blank parameter gets the neutral 30%. 3 critical + 6 other missing fields push confidence to 0. No crash. |
| 5 | **Junk**: title "xyzzy", requirement "asdfgh", email "asdf@@", phone "123", website "not a site", other fields blank | **23** | ❄️ Cold | 28% Low | Insufficient data to judge | 7/3/4/3/3/0/3. Three flags (invalid email, phone, website), unrecognised title, 5 missing fields. |
| 6 | **International**: Head of Sales, SaaS, London UK, 250 employees, Referral, "Need a CRM demo for our sales team asap", matching email, UK phone | **87** | 🔥 Hot | 100% High | Sales-ready, high-quality lead | 17/22/12/10/10/10/6. Strong intent (solution + urgency + demo request) and a referral. Outside India costs 4 location points but cannot stop a strong lead. |

## Other behaviour covered by the tests

| Area | What is checked |
|---|---|
| Intent cap | Urgency + budget + action words add up correctly and never exceed 25 |
| Company size parsing | "50–100 Employees", "50-100", "75", "1000+", "1,500", "", "abc", "0" |
| Job title tiers | Co-Founder, Managing Director, Vice President, Sales Head, Team Lead, Senior Analyst, Engineering Intern, unknown |
| Consistency | Every lead scored 100 times gives identical score, class, factors and hash. Extra spaces, capitals and `https://www.` do not change the score. |
| Bounds | Score always 0-100, equal to the sum of factors; no parameter exceeds its max (including empty and 5,000-character input) |
| Bulk CSV | Valid file ranked Hot first, case-insensitive columns, missing columns error, wrong-width and empty rows skipped and reported, 500-row cap, empty / binary file |
| LLM fallback | No API key uses templates; invalid JSON retried once; API errors fall back; guardrail rejects a wrong score or class; same lead twice hits the cache (all mocked, no real API calls) |

## Bulk demo file

[`data/sample_leads.csv`](../data/sample_leads.csv) contains the leads above plus five more (11 rows). Uploading it in the Bulk tab gives 4 Hot, 3 Warm and 4 Cold.
