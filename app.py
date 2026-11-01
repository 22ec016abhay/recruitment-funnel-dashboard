"""Recruitment Funnel & Source-of-Hire Dashboard (Streamlit).

Run:  streamlit run app.py

Every figure comes from sql/recruitment.db through a read-only connection.
LLM features (AI #2 brief, AI #3 questions) run only when you press their buttons,
and need GROQ_API_KEY in .env. Without a key the rest of the app still works.
"""
import os

import altair as alt
import pandas as pd
import streamlit as st

from src.agent.recruiting_agent import answer_question
from src.brief.brief_generator import generate_brief
from src.brief.facts_pack import generate_facts_pack
from src.fairness.fairness_check import run_fairness_audit
from src.label_mapping.llm_mapper import get_client

# On Streamlit Community Cloud the key lives in the app's secrets, not in .env.
# Copy it into the environment so get_client() finds it. Local runs use .env as before.
try:
    if "GROQ_API_KEY" in st.secrets and not os.environ.get("GROQ_API_KEY"):
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
except Exception:
    pass

ACCENT = "#0f766e"      # teal
ACCENT_2 = "#f59e0b"    # amber for warnings / highlights
MUTED = "#64748b"

st.set_page_config(page_title="Recruitment Funnel Dashboard", page_icon="📊", layout="wide")

CSS = f"""
<style>
  .hero {{
      background: linear-gradient(135deg, {ACCENT} 0%, #115e59 100%);
      color: white; padding: 1.6rem 2rem; border-radius: 16px; margin-bottom: 1.2rem;
      box-shadow: 0 6px 18px rgba(15,118,110,.25);
  }}
  .hero h1 {{ color: white; margin: 0; font-size: 2rem; }}
  .hero p  {{ margin: .4rem 0 0 0; opacity: .9; }}
  .kpi {{
      background: #ffffff; border: 1px solid #e2e8f0; border-radius: 14px;
      padding: 1rem 1.2rem; box-shadow: 0 1px 3px rgba(0,0,0,.05);
  }}
  .kpi .label {{ color: {MUTED}; font-size: .85rem; text-transform: uppercase; letter-spacing: .04em; }}
  .kpi .value {{ color: #0f172a; font-size: 1.9rem; font-weight: 700; margin-top: .2rem; }}
  .kpi .sub   {{ color: {MUTED}; font-size: .8rem; margin-top: .2rem; }}
  .pill {{
      display: inline-block; padding: .2rem .65rem; border-radius: 999px;
      font-size: .78rem; font-weight: 600; margin-right: .3rem;
  }}
  .pill-ok   {{ background: #dcfce7; color: #166534; }}
  .pill-warn {{ background: #fef3c7; color: #92400e; }}
  .pill-bad  {{ background: #fee2e2; color: #991b1b; }}
  .note {{
      background: #f8fafc; border-left: 4px solid {ACCENT}; padding: .8rem 1rem;
      border-radius: 8px; color: #334155; font-size: .92rem; margin: .6rem 0 1rem 0;
  }}
  .warn {{
      background: #fffbeb; border-left: 4px solid {ACCENT_2}; padding: .8rem 1rem;
      border-radius: 8px; color: #78350f; font-size: .92rem; margin: .6rem 0 1rem 0;
  }}
  div[data-testid="stTabs"] button {{ font-weight: 600; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def kpi(label, value, sub=""):
    st.markdown(
        f'<div class="kpi"><div class="label">{label}</div>'
        f'<div class="value">{value}</div><div class="sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def facts():
    return generate_facts_pack()


@st.cache_data(show_spinner=False)
def fairness(include_in_process: bool):
    return run_fairness_audit(include_in_process=include_in_process)


def llm_client():
    try:
        return get_client(provider="groq"), None
    except RuntimeError as e:
        return None, str(e)


st.markdown(
    '<div class="hero"><h1>📊 Recruitment Funnel & Source-of-Hire</h1>'
    '<p>1,500 synthetic applicants · funnel, sources, time-to-hire, fairness checks and AI tools. '
    'All figures computed from sql/recruitment.db.</p></div>',
    unsafe_allow_html=True,
)

tab_over, tab_brief, tab_fair, tab_ai = st.tabs([
    "📈 Overview", "📝 AI weekly brief", "⚖️ Fairness check", "🤖 Ask your funnel",
])

# ------------------------------------------------------------------ Overview
with tab_over:
    pack = facts()
    by_id = {f["id"]: f for f in pack["facts"]}
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("Applicants", f"{by_id['OV_01']['value']:,}", "unique candidates")
    with c2: kpi("Hires", f"{by_id['OV_02']['value']:,}", f"{by_id['OV_05']['value']}% hire rate")
    with c3: kpi("Still in process", f"{by_id['OV_04']['value']:,}", "not yet decided")
    with c4: kpi("Avg days to hire", f"{by_id['OV_06']['value']}", "hires only")

    st.write("")
    left, right = st.columns([1, 1])

    with left:
        st.subheader("Funnel")
        funnel = pd.DataFrame([
            {"stage": by_id[f"FN_{k}"]["label"].replace("Reached stage: ", ""),
             "count": by_id[f"FN_{k}"]["value"], "order": k}
            for k in range(1, 6)
        ])
        bars = alt.Chart(funnel).mark_bar(cornerRadius=6, color=ACCENT).encode(
            y=alt.Y("stage:N", sort=None, title=None),
            x=alt.X("count:Q", title="Applicants who reached this stage"),
            tooltip=["stage", "count"],
        )
        labels = bars.mark_text(align="left", dx=4, color="#0f172a").encode(text="count:Q")
        st.altair_chart((bars + labels).properties(height=260), width="stretch")
        conv = [by_id[f"FN_CV_{k}"] for k in range(2, 6)]
        st.markdown(
            '<div class="note">Conversion from the previous stage: ' +
            " · ".join(f"{c['label'].replace('Conversion into ', '')} {c['value']}%" for c in conv) +
            "</div>", unsafe_allow_html=True)

    with right:
        st.subheader("Hire rate by source")
        rows = []
        for f in pack["facts"]:
            if f["id"].startswith("SRC_") and f["id"].endswith("_R"):
                rows.append({"source": f["label"].split(" - ")[0].replace("Source: ", ""),
                             "rate": f["value"], "few_hires": bool(f["note"])})
        src = pd.DataFrame(rows).sort_values("rate", ascending=False)
        chart = alt.Chart(src).mark_bar(cornerRadius=6).encode(
            y=alt.Y("source:N", sort="-x", title=None),
            x=alt.X("rate:Q", title="Hire rate (%)"),
            color=alt.condition(alt.datum.few_hires, alt.value(ACCENT_2), alt.value(ACCENT)),
            tooltip=["source", "rate"],
        )
        st.altair_chart(chart.properties(height=260), width="stretch")
        st.markdown('<div class="note">Amber bars have fewer than 10 hires, so treat those rates as unstable.</div>',
                    unsafe_allow_html=True)

    st.subheader("Cohorts and open outcomes")
    st.markdown(
        f'<div class="warn"><b>{by_id["CAV_01"]["value"]} monthly cohorts</b> after June 2026 still have open outcomes '
        f'({by_id["CAV_02"]["value"]} applicants). Hire rates for those months are not yet comparable.</div>',
        unsafe_allow_html=True)
    months = pd.DataFrame([
        {"month": f["id"].replace("MON_", "").replace("_R", ""), "rate": f["value"]}
        for f in pack["facts"] if f["id"].startswith("MON_") and f["id"].endswith("_R")
    ])
    months["mature"] = months["month"] <= pack["mature_cutoff"]
    line = alt.Chart(months).mark_bar(cornerRadius=4).encode(
        x=alt.X("month:N", title="Applied month", sort=None),
        y=alt.Y("rate:Q", title="Hire rate (%)"),
        color=alt.condition(alt.datum.mature, alt.value(ACCENT), alt.value("#cbd5e1")),
        tooltip=["month", "rate", "mature"],
    )
    st.altair_chart(line.properties(height=240), width="stretch")
    st.caption("Grey bars are immature cohorts (outcomes still open).")

# ------------------------------------------------------------------ AI #2
with tab_brief:
    st.subheader("Weekly brief")
    st.markdown(
        '<div class="note">The facts are computed in code. The LLM writes the narrative, and every number and '
        'citation is checked against the facts before it is shown.</div>', unsafe_allow_html=True)
    with st.expander("Facts the model may use"):
        st.dataframe(pd.DataFrame(facts()["facts"]), width="stretch", hide_index=True)
    if st.button("✨ Generate brief", type="primary"):
        client, err = llm_client()
        if client is None:
            st.error(err)
        else:
            try:
                with st.spinner("Writing the brief (rate-limited calls may wait a minute)..."):
                    out = generate_brief(client)
            except Exception as e:  # e.g. rate limit after retries, network, quota
                st.error(f"The model call failed: {type(e).__name__}. Wait a minute and try again.")
            else:
                if out["status"] == "OK":
                    st.markdown('<span class="pill pill-ok">Validated</span>'
                                f'<span class="pill pill-ok">{len(out["attempts"])} attempt(s)</span>',
                                unsafe_allow_html=True)
                    st.markdown(out["brief"])
                else:
                    st.markdown('<span class="pill pill-bad">Not verified</span>', unsafe_allow_html=True)
                    st.error("The text below failed validation. Do not use it without checking.")
                    st.markdown(out["brief"])
                with st.expander("Validation details"):
                    st.json(out["validation"])

# ------------------------------------------------------------------ AI #5
with tab_fair:
    st.subheader("Gender selection rates (synthetic data)")
    st.markdown(
        '<div class="warn"><b>Screening heuristic, not a legal analysis.</b> It describes this synthetic dataset only. '
        'Non-binary (n = 46) is flagged and not interpreted.</div>', unsafe_allow_html=True)
    scope = st.radio("Scope", ["All applicants", "Excluding In Process"], horizontal=True)
    res = fairness(scope == "All applicants")
    table = res["stage_table"]
    order = ["Screened", "Interviewed", "Offered", "Hired"]

    base = alt.Chart(table).encode(
        x=alt.X("stage:N", sort=order, title=None),
        xOffset="gender:N",
        color=alt.Color("gender:N", scale=alt.Scale(
            domain=["Female", "Male", "Non-binary"], range=[ACCENT, "#334155", ACCENT_2]), title="Gender"),
    )
    bars = base.mark_bar(cornerRadius=4).encode(
        y=alt.Y("rate_pct:Q", title="Share reaching stage (%)"),
        tooltip=["gender", "stage", "n", "reached", "rate_pct", "ci95_low_pct", "ci95_high_pct"],
    )
    ci = base.mark_errorbar().encode(y=alt.Y("ci95_low_pct:Q", title="Share reaching stage (%)"),
                                     y2=alt.Y2("ci95_high_pct:Q"))
    st.altair_chart((bars + ci).properties(height=340), width="stretch")
    st.caption("Bars: share of each gender reaching the stage. Whiskers: 95% Wilson interval.")

    st.markdown("**Adverse-impact ratio** (reference = highest rate among groups with n ≥ 50)")
    st.dataframe(res["impact"][["stage", "gender", "n", "rate_pct", "impact_ratio", "below_4_5ths", "low_n"]],
                 width="stretch", hide_index=True)
    st.markdown("**Fisher exact test, Female vs Male**")
    st.dataframe(res["tests"], width="stretch", hide_index=True)

# ------------------------------------------------------------------ AI #3
EXAMPLES = [
    "What is the hire rate for Referral candidates?",
    "How many applicants reached the offer stage?",
    "How many applicants are still in process?",
    "What is the average days to hire for each source?",
]

with tab_ai:
    st.subheader("Ask your funnel")
    st.markdown(
        '<div class="note">The model proposes one read-only SQL query at a time. Code checks each query before it runs, '
        'and every answer shows the SQL that produced it.</div>', unsafe_allow_html=True)
    st.write("Try:")
    cols = st.columns(len(EXAMPLES))
    for col, ex in zip(cols, EXAMPLES):
        if col.button(ex, key=ex):
            st.session_state["q"] = ex
    question = st.text_input("Your question", key="q", placeholder="e.g. Which source has the most hires?")
    if st.button("Ask", type="primary", disabled=not question.strip()):
        client, err = llm_client()
        if client is None:
            st.error(err)
        else:
            try:
                with st.spinner("Thinking..."):
                    out = answer_question(question, client=client)
            except Exception as e:
                st.error(f"The model call failed: {type(e).__name__}. Wait a minute and try again.")
            else:
                status_pill = {"answered": "pill-ok", "refused": "pill-warn"}.get(out["status"], "pill-bad")
                st.markdown(f'<span class="pill {status_pill}">{out["status"]}</span>'
                            f'<span class="pill pill-warn">{out.get("steps", 0)} step(s)</span>',
                            unsafe_allow_html=True)
                st.markdown(out.get("answer", ""))
                if out.get("sql"):
                    with st.expander("SQL that was run", expanded=True):
                        for sql in out["sql"]:
                            st.code(sql, language="sql")
                if out.get("rows"):
                    st.dataframe(pd.DataFrame(out["rows"], columns=out.get("columns")),
                                 width="stretch", hide_index=True)