"""LeadPulse Streamlit app: score a lead, bulk-score a CSV, see how scoring works."""

import html
import os
import re
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from leadpulse.bulk import BulkError, score_csv, template_csv
from leadpulse.config_loader import load_config
from leadpulse.llm import generate_insights, llm_status
from leadpulse.models import FIELD_LABELS, SAMPLE_LEAD_FIELDS, LeadInput, LLMInsights, ScoreResult
from leadpulse.scoring import compare_factors, score_lead

ROOT = Path(__file__).parent
SIZE_OPTIONS = ["", "1-10", "11-50", "51-200", "201-1000", "1000+"]
SOURCE_OPTIONS = ["", "Website", "Referral", "Demo request", "Event", "Webinar", "LinkedIn",
                  "Email campaign", "Cold outreach", "Purchased list", "Other"]
INDIGO, SLATE_LIGHT = "#4F46E5", "#E2E8F0"
CLASS_COLOURS = {"Hot": "#EF4444", "Warm": "#F59E0B", "Cold": "#3B82F6"}

st.set_page_config(page_title="LeadPulse · AI Lead Scoring", page_icon=str(ROOT / "assets" / "icon.png"),
                   layout="wide")
# Strip CSS comments: the brand kit's header comment contains a literal "</style>" that would end the tag early.
_css = re.sub(r"/\*.*?\*/", "", (ROOT / "assets" / "style.css").read_text(encoding="utf-8"), flags=re.S)
st.html(f"<style>{_css}</style>")


def _secrets_to_env() -> None:
    """On Streamlit Cloud the keys live in st.secrets; locally they come from .env."""
    try:
        for name in ("LLM_PROVIDER", "GEMINI_API_KEY", "GROQ_API_KEY", "LLM_MODEL"):
            if name in st.secrets:
                os.environ.setdefault(name, str(st.secrets[name]))
    except Exception:  # no secrets.toml at all
        pass


def _choice(label: str, options: list[str], key: str) -> str:
    """Dropdown that also accepts free text and keeps a loaded value that is not in the list."""
    current = st.session_state.get(key, "")
    opts = options if current in options else [*options, current]
    return st.selectbox(label, opts, key=key, accept_new_options=True) or ""


def _card(title: str, body: str) -> None:
    st.markdown(f'<div class="lp-card"><div style="color:#64748B;font-weight:500">{title}</div>{body}</div>',
                unsafe_allow_html=True)


def _badge(classification: str) -> str:
    return f'<span class="lp-badge lp-{classification.lower()}">{classification}</span>'


def _factor_chart(result: ScoreResult) -> go.Figure:
    labels = [f.label for f in reversed(result.factors)]
    fig = go.Figure([
        go.Bar(y=labels, x=[f.max_points for f in reversed(result.factors)], orientation="h",
               marker_color=SLATE_LIGHT, name="Max", hovertemplate="Max %{x}<extra></extra>"),
        go.Bar(y=labels, x=[f.points for f in reversed(result.factors)], orientation="h",
               marker_color=INDIGO, name="Points", text=[f"{f.points}/{f.max_points}" for f in reversed(result.factors)],
               textposition="outside", hovertemplate="%{x} points<extra></extra>"),
    ])
    fig.update_layout(barmode="overlay", height=300, margin=dict(l=0, r=30, t=10, b=0), showlegend=False,
                      xaxis=dict(range=[0, 27], title="Points"), font=dict(family="Inter, sans-serif"))
    return fig


def _sidebar() -> None:
    with st.sidebar:
        st.image(str(ROOT / "assets" / "logo.svg"), width=190)
        st.markdown("**Know which leads are alive.**")
        provider = llm_status()
        if provider:
            st.success(f"AI explanations: {provider} ✓")
        else:
            st.info("Offline mode (rule-based explanations)")
        st.markdown("#### How it works")
        st.markdown("- **Rules score** every lead on 7 weighted parameters (0-100).\n"
                    "- **Data checks** flag bad emails, phones and websites.\n"
                    "- **AI explains** the result and drafts a follow-up. It never changes the score.")


def _lead_form() -> None:
    if st.button("Load sample lead"):
        for field, value in SAMPLE_LEAD_FIELDS.items():
            st.session_state[f"f_{field}"] = value
    with st.form("lead_form"):
        left, right = st.columns(2)
        values = {}
        with left:
            for field in ("name", "company", "website", "job_title", "industry"):
                values[field] = st.text_input(FIELD_LABELS[field], key=f"f_{field}")
            values["location"] = st.text_input(FIELD_LABELS["location"], key="f_location",
                                               placeholder="e.g. Bangalore")
        with right:
            values["company_size"] = _choice(FIELD_LABELS["company_size"], SIZE_OPTIONS, "f_company_size")
            values["lead_source"] = _choice(FIELD_LABELS["lead_source"], SOURCE_OPTIONS, "f_lead_source")
            values["email"] = st.text_input(FIELD_LABELS["email"], key="f_email")
            values["phone"] = st.text_input(FIELD_LABELS["phone"], key="f_phone", placeholder="+91 98765 43210")
            values["requirement"] = st.text_area(FIELD_LABELS["requirement"], key="f_requirement", height=122)
        submitted = st.form_submit_button("Score lead", type="primary")

    if submitted:
        if not any(v.strip() for v in values.values()):
            st.warning("Please fill in at least one field (or click **Load sample lead**).")
            return
        lead = LeadInput(**values)
        st.session_state.lead, st.session_state.result = lead, score_lead(lead)
        st.session_state.insights = None
        for field in ("job_title", "company_size", "lead_source", "requirement", "email"):
            st.session_state[f"w_{field}"] = getattr(lead, field)


def _render_result(lead: LeadInput, result: ScoreResult, insights: LLMInsights) -> None:
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        _card("Lead score", f'<div class="lp-score">{result.score}<small>/100</small></div>'
                            f'<div style="margin-top:8px">{_badge(result.classification)}</div>')
    with c2:
        _card("Confidence", f'<div class="lp-score">{result.confidence}<small>%</small></div>'
                            f'<div style="margin-top:8px;font-weight:600">{result.confidence_label}</div>')
    with c3:
        note = html.escape(insights.quality_note) if insights.source == "llm" else ""
        _card("Quality assessment", f'<div style="font-size:1.35rem;font-weight:700;margin-top:6px">'
                                    f'{html.escape(result.quality_label)}</div><div>{note}</div>')

    st.markdown("#### Score breakdown")
    st.plotly_chart(_factor_chart(result), width="stretch", config={"displayModeBar": False})

    pos, neg = st.columns(2)
    with pos:
        st.markdown("#### Positive factors")
        for line in result.positive_factors or ["None"]:
            st.markdown(f'<div class="lp-plus">+ {html.escape(line)}</div>', unsafe_allow_html=True)
    with neg:
        st.markdown("#### Negative factors")
        for line in result.negative_factors or ["None"]:
            st.markdown(f'<div class="lp-minus">- {html.escape(line)}</div>', unsafe_allow_html=True)

    st.markdown("#### Data-quality checks")
    if result.flags:
        st.warning("\n".join(f"- {flag}" for flag in result.flags))
    else:
        st.success("No data-quality issues found.")

    st.markdown("#### Scoring explanation")
    st.write(insights.explanation)
    if insights.source == "template":
        st.caption("Offline mode (rule-based explanations)")

    st.markdown("#### Recommended next action")
    st.info(insights.next_action)

    st.markdown("#### AI follow-up email")
    st.code(f"Subject: {insights.follow_up_email.subject}\n\n{insights.follow_up_email.body}",
            language=None, wrap_lines=True)
    st.caption(f"Scoring version {result.scoring_version} · input hash {result.input_hash[:12]}")


def _what_if(lead: LeadInput, result: ScoreResult) -> None:
    with st.expander("What-If Simulator: change a field and see the score move instantly"):
        st.caption("Rule engine only, no AI call. Same inputs always give the same score.")
        a, b = st.columns(2)
        with a:
            job_title = st.text_input("Job Title", key="w_job_title")
            company_size = _choice("Company Size", SIZE_OPTIONS, "w_company_size")
            lead_source = _choice("Lead Source", SOURCE_OPTIONS, "w_lead_source")
        with b:
            email = st.text_input("Email", key="w_email")
            requirement = st.text_area("Requirement", key="w_requirement", height=122)
        changed = lead.model_copy(update=dict(job_title=job_title, company_size=company_size,
                                              lead_source=lead_source, email=email, requirement=requirement))
        new = score_lead(changed)
        m1, m2, m3 = st.columns(3)
        m1.metric("New score", new.score, delta=new.score - result.score)
        m2.markdown(f"New class<br>{_badge(new.classification)}", unsafe_allow_html=True)
        m3.metric("New confidence", f"{new.confidence}% {new.confidence_label}",
                  delta=new.confidence - result.confidence)
        changes = compare_factors(result, new)
        for label, old, now in changes:
            css = "lp-plus" if now > old else "lp-minus"
            st.markdown(f'<div class="{css}">{label}: {old} → {now}, {now - old:+d}</div>', unsafe_allow_html=True)
        if not changes:
            st.caption("No factor changed yet. Edit a field above.")


def _score_tab() -> None:
    _lead_form()
    if "result" not in st.session_state:
        return
    lead, result = st.session_state.lead, st.session_state.result
    if st.session_state.insights is None:
        with st.spinner("Writing the explanation..."):
            st.session_state.insights = generate_insights(lead, result)
    st.divider()
    _render_result(lead, result, st.session_state.insights)
    _what_if(lead, result)


def _bulk_tab() -> None:
    st.markdown("Upload a CSV with the 11 lead columns (max 500 rows). Every row is scored by the rule engine.")
    d1, d2, _ = st.columns([1, 1, 2])
    d1.download_button("Download CSV template", template_csv(), "lead_template.csv", "text/csv")
    d2.download_button("Download sample leads", (ROOT / "data" / "sample_leads.csv").read_bytes(),
                       "sample_leads.csv", "text/csv")
    upload = st.file_uploader("Upload leads CSV", type=["csv"])
    if upload is None:
        return
    try:
        bulk = score_csv(upload.getvalue())
    except BulkError as exc:
        st.error(str(exc))
        return
    if bulk.errors:
        st.warning(f"{len(bulk.errors)} issue(s) while reading the file:\n"
                   + "\n".join(f"- {e}" for e in bulk.errors[:20]))

    counts = bulk.table["Class"].value_counts()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Leads scored", len(bulk.table))
    k2.metric("🔥 Hot", int(counts.get("Hot", 0)))
    k3.metric("🌤 Warm", int(counts.get("Warm", 0)))
    k4.metric("❄️ Cold", int(counts.get("Cold", 0)))

    styled = bulk.table.style.map(
        lambda c: f"background-color:{CLASS_COLOURS[c]};color:white;font-weight:600", subset=["Class"])
    st.dataframe(styled, width="stretch", hide_index=True)
    st.download_button("Download results CSV", bulk.to_csv(), "leadpulse_results.csv", "text/csv", type="primary")

    st.markdown("#### AI explanation for one lead")
    labels = [f"#{i + 1} {lead.name or '(no name)'} ({r.score}, {r.classification})"
              for i, (lead, r) in enumerate(bulk.results)]
    pick = st.selectbox("Choose a lead", range(len(labels)), format_func=labels.__getitem__)
    if st.button("Explain this lead"):
        lead, result = bulk.results[pick]
        insights = generate_insights(lead, result)
        st.write(insights.explanation)
        st.info(insights.next_action)
        st.code(f"Subject: {insights.follow_up_email.subject}\n\n{insights.follow_up_email.body}",
                language=None, wrap_lines=True)


def _rules_text(rules: dict) -> str:
    if "tiers" in rules:
        text = " · ".join(f"{t['name']} {t['points']}" for t in rules["tiers"])
        fallback = "unrecognised" if rules.get("flag_unrecognised", True) else "other"
        return f"{text} · {fallback} {rules['unrecognised_points']}"
    if "buckets" in rules:
        return " · ".join(f"{b['name']} employees {b['points']}" for b in rules["buckets"])
    if "signals" in rules:
        signals = " · ".join(f"{name} +{s['points']}" for name, s in rules["signals"].items())
        return (f"Base {rules['base']} · {signals} · capped at {rules['max']} · "
                f"fewer than {rules['short_text_words']} words and no keyword = {rules['short_text_points']}")
    return " · ".join(f"{name.replace('_', ' ')} {pts}" for name, pts in rules["checks"].items())


def _how_tab() -> None:
    config = load_config()
    st.info("The score is computed by rules. The AI only explains it.")
    st.markdown("#### Parameters and weights (total 100)")
    st.table(pd.DataFrame(
        [{"Parameter": r["label"], "Max points": r["max"], "Rules": _rules_text(r)}
         for r in config["parameters"].values()]
    ).set_index("Parameter"))
    t = config["classification"]
    c = config["confidence"]
    a, b = st.columns(2)
    with a:
        st.markdown("#### Classification")
        st.markdown(f"{_badge('Hot')} score ≥ {t['hot']}  \n{_badge('Warm')} {t['warm']} to {t['hot'] - 1}  \n"
                    f"{_badge('Cold')} below {t['warm']}", unsafe_allow_html=True)
        st.markdown("#### Missing data")
        st.markdown(f"A blank field gets a neutral {int(config['missing_neutral_ratio'] * 100)}% of that "
                    "parameter's points, is listed as a negative factor and lowers confidence.")
    with b:
        st.markdown("#### Confidence")
        st.markdown(
            f"Start at {c['start']} and subtract:\n"
            f"- missing critical field (Job Title, Requirement, Company Size, or both Email and Phone): "
            f"-{c['missing_critical']}\n"
            f"- any other missing field: -{c['missing_other']}\n"
            f"- unrecognised value needing a default: -{c['unrecognised']}\n"
            f"- each data-quality flag: -{c['flag']}\n\n"
            f"**High** ≥ {c['labels']['high']} · **Medium** {c['labels']['medium']}-{c['labels']['high'] - 1}"
            f" · **Low** below {c['labels']['medium']}"
        )
    st.caption(f"Scoring version {config['scoring_version']} · read live from scoring_config.yaml")


_secrets_to_env()
_sidebar()
st.title("LeadPulse")
st.caption("Explainable lead scoring: rules score, AI explains.")
tab1, tab2, tab3 = st.tabs(["Score a Lead", "Bulk Score (CSV)", "How Scoring Works"])
with tab1:
    _score_tab()
with tab2:
    _bulk_tab()
with tab3:
    _how_tab()
