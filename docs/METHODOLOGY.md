# LeadPulse Scoring Methodology

LeadPulse scores every lead from 0 to 100 with a **weighted, rule-based engine**. The same input always gives the same score. An LLM is used only afterwards, to explain the result in plain English and draft a follow-up email. It never produces or changes the score.

Every number on this page lives in [`leadpulse/config/scoring_config.yaml`](../leadpulse/config/scoring_config.yaml). The app's "How Scoring Works" tab renders the same file, so the documentation and the engine cannot drift apart.

## Assumed business context

The seller offers **B2B business software (CRM / sales automation) to SMB and mid-market companies, primarily in India**. The weights below encode that: decision makers, explicit software needs, 51-200 employee companies and Indian metros score highest. A different seller would edit the YAML, not the code.

## 1. Parameters and weights (total = 100)

| # | Parameter | Field | Max | Why this weight |
|---|---|---|---|---|
| 1 | Buying intent | Requirement | **25** | The strongest single predictor: a lead who names a product and a timeline is far more likely to buy than one who is "just browsing". |
| 2 | Decision authority | Job Title | **20** | B2B deals stall without someone who can sign. Founders and directors shorten the sales cycle. |
| 3 | Company size | Company Size | **15** | Fit for SMB / mid-market software. Very small firms have little budget, very large ones buy through long procurement. |
| 4 | Industry fit | Industry | **10** | Some industries adopt CRM faster than others. Important, but a good lead from a medium-fit industry should not be buried. |
| 5 | Lead source | Lead Source | **10** | Referrals and inbound requests convert much better than cold or purchased lists. |
| 6 | Contact & data quality | Email, Phone, Website | **10** | A lead that cannot be reached, or uses fake details, is worth less however good it looks. |
| 7 | Market / location fit | Company Location | **10** | Primary market is India. Tier-1 metros have the densest SMB tech adoption. |

### 1.1 Decision authority (max 20)

Tiers are checked **in this order and the first match wins**:

| Order | Tier | Keywords (examples) | Points |
|---|---|---|---|
| 1 | Entry level | intern, student, trainee, junior, fresher | 3 |
| 2 | VP / Head | VP, vice president, head, head of | 17 |
| 3 | Founder / C-level / Director | founder, co-founder, owner, CEO, CTO, CXO, MD, president, director | 20 |
| 4 | Manager / Team lead | manager, team lead, lead, supervisor | 12 |
| 5 | Individual contributor | senior, specialist, executive, analyst, engineer | 7 |
| - | Not recognised | anything else | 7, flagged "unrecognised" |

The order prevents two classic mistakes: "Engineering Intern" is not read as an engineer, and "Vice President" is not read as "President".

### 1.2 Buying intent (max 25)

| Signal | Example keywords | Points |
|---|---|---|
| Any non-empty requirement | | base 5 |
| Specific solution | CRM, software, ERP, automation, platform, tool, lead management, sales | +10 |
| Urgency | urgent, asap, immediately, this week, this month, soon, quickly | +5 |
| Budget | budget, ₹, rs, lakh, $, pricing approved, allocated | +3 |
| Action request | demo, quote, pricing, call, trial, proposal | +2 |

The total is capped at 25. A requirement shorter than 3 words with no keyword at all (for example "hello there") scores **3 in total**.

### 1.3 Company size (max 15)

| Employees | Points |
|---|---|
| 1-10 | 5 |
| 11-50 | 10 |
| 51-200 | 15 |
| 201-1000 | 12 |
| more than 1000 | 9 |

Parsing: "50-100", "50–100 Employees" and "50-100 employees" use the **midpoint** (75). "75" is 75. "1000+" means *more than* 1000, so it falls in the top band. Text with no number ("abc") gets a default of 4 and is flagged "unrecognised".

### 1.4 Industry fit (max 10)

High fit (10): IT services, software, SaaS, technology, e-commerce, fintech, real estate, education, healthcare, consulting, marketing / agency.
Medium fit (6): manufacturing, retail, logistics, finance, hospitality, media.
Any other industry: 3. This is a legitimate "low fit" answer, so it does **not** lower confidence.

### 1.5 Lead source (max 10)

Referral 10 · Website / inbound / demo request 9 · Event / webinar 7 · LinkedIn / social 6 · Email campaign 5 · Cold outreach / purchased list / other 3. An unrecognised source also gets 3 and is flagged.

### 1.6 Contact & data quality (max 10)

| Check | Points |
|---|---|
| Email has a valid format | 2 |
| Business email (not a free provider, not a placeholder / disposable domain) | 3 |
| Email domain matches the website domain (subdomains count) | 2 |
| Phone is valid (Google's `phonenumbers` library, default region India) | 3 |

Only what is available is scored. A missing email or phone simply earns 0 for those checks.

### 1.7 Market / location fit (max 10)

Tier-1 Indian metro (Bangalore / Bengaluru, Mumbai, Delhi / NCR, Gurgaon / Gurugram, Noida, Hyderabad, Chennai, Pune, Kolkata) 10 · other Indian city or state 7 · outside India 6. A location that matches none of the lists also gets 6 and is flagged "unrecognised".

## 2. Data-quality checks

Each flag is shown in the UI, lowers confidence by 5 and is added to the next action as "Verify contact details (...)".

| Flag | Rule |
|---|---|
| Invalid email format | Does not look like `name@domain.tld` |
| Free email provider | gmail, yahoo, outlook, hotmail, rediffmail, ... |
| Placeholder or disposable email domain | example.com, test.com, mailinator, yopmail, ... |
| Email domain does not match website | Both are valid but the domains differ |
| Invalid phone number | `phonenumbers` says the number is not valid |
| Invalid website | A website was typed but it is not a domain |

## 3. Missing data policy

- A blank field gets a **neutral 30% of its parameter's max, rounded down** (Job Title 6, Requirement 7, Company Size 4, Industry 3, Source 3, Location 3). This keeps the lead from being rewarded or punished for something we simply don't know.
- The blank field is listed as a negative factor ("Job Title not provided") and lowers confidence.
- Contact & data quality is the exception: only what is available is scored.
- A missing website is counted **once**, as a missing field. It is not also flagged as "invalid website".
- Name and Company can be empty. Empty, garbage or extremely long input never crashes the engine (cells are capped at 1,000 characters).

## 4. Classification

| Class | Score |
|---|---|
| 🔥 Hot | 75 or more |
| 🌤 Warm | 45 to 74 |
| ❄️ Cold | below 45 |

## 5. Confidence

Confidence says how sure the system is about its own score, separately from the score itself. It starts at 100 and subtracts:

| Issue | Penalty |
|---|---|
| Missing critical field: Job Title, Requirement, Company Size, or **both** Email and Phone | -20 each |
| Any other missing field | -8 each |
| Unrecognised value that needed a default (title, size, source, location) | -5 each |
| Each data-quality flag | -5 each |

The result is clamped to 0-100. Labels: **High** 80 or more, **Medium** 50-79, **Low** below 50.

Note: confidence measures *missing and broken* data. A lead where every field is filled with gibberish but nothing is blank loses about 35 points and lands at Medium. Real junk leads are usually also incomplete, which pushes them to Low (see the junk test case).

## 6. Quality assessment and next action

| Condition | Quality label |
|---|---|
| Confidence below 30 (any score) | Insufficient data to judge |
| Hot, confidence High or Medium | Sales-ready, high-quality lead |
| Hot, confidence Low | High potential, verify details first |
| Warm | Promising lead, needs nurturing |
| Cold | Low fit / low intent lead |

| Class | Base next action |
|---|---|
| Hot | Call within 24 hours and offer a product demo |
| Warm | Send a personalised email with a relevant case study; follow up in 3-5 days |
| Cold | Add to a nurture email campaign; re-evaluate in 30 days |

If any data-quality flag exists, the action becomes "Verify contact details (*flags*), then *base action*". The LLM may reword this, but the base action is fixed by the rules.

## 7. Determinism and the role of the LLM

- Scoring is a set of pure functions: no randomness, no clock, no network, no LLM.
- Inputs are normalised first (trim, lowercase, collapse spaces, strip `http(s)://` and `www.`), so formatting noise cannot change the score.
- Every result carries `scoring_version` (1.0.0) and `input_hash` (SHA-256 of the normalised input).
- The LLM receives the finished result and must return strict JSON (validated with Pydantic). It runs at temperature 0. Invalid JSON is retried once.
- **Guardrail:** if the LLM's text states a different score or a different Hot/Warm/Cold class, its answer is discarded and a rule-based template is used.
- LLM answers are cached on disk, keyed by input hash + scoring version + prompt version + model, so the same lead always gets the same explanation and no repeat API calls.
- With no API key, or on any API error, the app works fully offline with template explanations.

## 8. Worked example: the sample lead

| Field | Value |
|---|---|
| Name | Rahul Sharma |
| Company / Website | ABC Technologies / www.abctechnologies.com |
| Job Title | Founder |
| Industry / Location | IT Services / Bangalore |
| Company Size | 50–100 Employees |
| Lead Source | Website |
| Requirement | Looking for CRM software |
| Email / Phone | rahul@example.com / +91 9876543210 |

| Parameter | Points | Reason |
|---|---|---|
| Decision authority | 20 / 20 | Founder |
| Buying intent | 15 / 25 | base 5 + specific solution 10 ("crm", "software") |
| Company size | 15 / 15 | midpoint 75, in the 51-200 band |
| Industry fit | 10 / 10 | IT services is high fit |
| Lead source | 9 / 10 | Website is inbound |
| Contact & data quality | 5 / 10 | valid format 2 + valid phone 3; example.com is a placeholder and does not match the website |
| Market / location fit | 10 / 10 | Bangalore is a tier-1 metro |
| **Total** | **84** | **Hot** |

Confidence: 100 - 5 (placeholder email) - 5 (domain mismatch) = **90%, High**.
Quality: **Sales-ready, high-quality lead**.
Next action: **Verify contact details (placeholder or disposable email domain, email domain does not match website), then call within 24 hours and offer a product demo.**
