"""
Optional Streamlit lab for county AP register exploration.

NOT the production county queue — use POST /run-sync for 92-county factory.
Run: cd /root/ReClaw-2.0 && PYTHONPATH=. streamlit run scratch/county-anomaly-lab/app.py

Requires: pip install -r scratch/county-anomaly-lab/requirements.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.transaction_anomaly import (  # noqa: E402
    detect_all_transactions,
    detect_isolation_forest,
    detect_rule_flags,
    load_transactions,
    monthly_anomaly_counts,
)

st.set_page_config(page_title="County Anomaly Lab", layout="wide")
st.title("Indiana County Transaction Anomaly Lab")
st.caption(
    "Upload AP register / check register CSV. Gateway disbursements lack payment dates — "
    "use ReClaw `red_flag_engine` for those."
)

col_a, col_b = st.columns(2)
with col_a:
    county = st.text_input("County name", value="Spencer")
with col_b:
    uploaded = st.file_uploader("AP register CSV or Excel", type=["csv", "xlsx", "xls"])

sample_path = REPO / "data" / "inbox"
if sample_path.exists():
    samples = sorted(sample_path.glob("*.csv"))[:5]
    if samples:
        pick = st.selectbox("Or load from data/inbox/", ["—"] + [p.name for p in samples])
        if pick != "—":
            chosen = next(p for p in samples if p.name == pick)
            uploaded = open(chosen, "rb")

if not uploaded:
    st.info(
        "Drop a check register with vendor, amount, and ideally payment_date. "
        "Production pipeline: `curl -X POST 'http://127.0.0.1:8000/run-sync?county=Spencer'`"
    )
    st.stop()

tmp = REPO / "data" / "cache" / "_lab_upload.csv"
tmp.parent.mkdir(parents=True, exist_ok=True)
tmp.write_bytes(uploaded.read())

try:
    df, flags = detect_all_transactions(tmp, county=county)
except Exception as exc:
    st.error(f"Could not parse file: {exc}")
    st.stop()

st.success(f"Loaded {len(df):,} transactions · {len(flags)} flags")

m1, m2, m3 = st.columns(3)
m1.metric("Total spend", f"${df['amount'].sum():,.0f}")
m2.metric("Unique vendors", f"{df['vendor'].nunique():,}")
m3.metric("Date coverage", "Yes" if "date" in df.columns and df["date"].notna().any() else "No")

tab_chart, tab_flags, tab_chat = st.tabs(["Charts", "Flags", "Explain"])

with tab_chart:
    monthly = monthly_anomaly_counts(df)
    if not monthly.empty:
        fig = px.bar(monthly, x="month", y="total_amount", title="Monthly disbursements")
        st.plotly_chart(fig, use_container_width=True)
    top_v = df.groupby("vendor")["amount"].sum().nlargest(15).reset_index()
    fig2 = px.bar(top_v, x="amount", y="vendor", orientation="h", title="Top 15 vendors")
    st.plotly_chart(fig2, use_container_width=True)

with tab_flags:
    if not flags:
        st.write("No flags at current thresholds.")
    else:
        rows = [
            {
                "severity": f.severity,
                "category": f.category,
                "description": f.description,
                "evidence": f.evidence[:200],
            }
            for f in flags
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

with tab_chat:
    st.markdown("**Local explain (no cloud)** — summarize top flags")
    if st.button("Summarize with Ollama (if running on :8080)"):
        try:
            import httpx

            top = flags[:5]
            prompt = (
                f"Summarize these {county} County public-record anomalies in plain English "
                f"for taxpayers. Fair-report only, no crime allegations:\n"
                + "\n".join(f"- {f.description}" for f in top)
            )
            r = httpx.post(
                "http://127.0.0.1:8080/api/generate",
                json={"model": "llama3", "prompt": prompt, "stream": False},
                timeout=60.0,
            )
            if r.status_code == 200:
                st.write(r.json().get("response", r.text))
            else:
                st.warning(f"Ollama returned {r.status_code} — start Ollama or skip this panel.")
        except Exception as exc:
            st.warning(f"Ollama unavailable: {exc}")
    else:
        st.write("Click to generate a plain-English summary of the top 5 flags.")