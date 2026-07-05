"""
Silent Auditor Agent — ReClaw 2.0

Performs deep compliance, red-flag, and budget anomaly audits for counties.
Integrates with the DOGEGPT anomaly detection pipeline (IsolationForest, ECOD, robust z-scores).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from core.config import get_settings
from core.handoff import (
    CompliancePackage,
    RedFlag,
)
from core.security import SecurityManager
from core.session import Session

def _load_audit_pipeline():
    """Lazy-load pandas + DOGEGPT detectors (optional heavy deps)."""
    import pandas as pd

    sys.path.append(str(Path("/root/DOGEGPT_AD_STARTER")))
    try:
        from pipeline_budget_anomalies import load_data, timeseries_anomalies, crosssection_anomalies
    except ImportError:
        def load_data(path):
            return pd.DataFrame()

        def timeseries_anomalies(df, min_years=3):
            return pd.DataFrame()

        def crosssection_anomalies(df):
            return pd.DataFrame()

    return pd, load_data, timeseries_anomalies, crosssection_anomalies


class SilentAuditorAgent:
    """
    Silent Auditor Agent.

    OpenClaw patterns:
    - Loads agents/silent_auditor/SOUL.md via session.
    - Requires 'compliance_audit' capability (HIGH risk, gates execution).
    - Writes compliance handoff to session.
    """

    SOUL_PATH = Path(__file__).parent / "silent_auditor" / "SOUL.md"

    def __init__(self, settings: Any | None = None, session: Session | None = None):
        self.settings = settings or get_settings()
        self.session = session
        self.security: SecurityManager | None = None
        if self.session:
            self.security = SecurityManager(self.session.base_dir, self.session.session_id)
            soul_text = self.session.load_soul("silent_auditor", self.SOUL_PATH)
            self.session.log(f"Silent Auditor SOUL loaded (len={len(soul_text)} chars)")

    def run(self, county: str, source_file: str | None = None) -> CompliancePackage:
        """
        Runs the full DOGEGPT budget anomaly detection pipeline for a county.
        """
        if self.session:
            self.session.log(f"Silent Auditor starting audit for county: {county}")
            if self.security:
                # Check for explicit capability grant (this is high risk!)
                if not self.security.is_granted("compliance_audit"):
                    self.session.log("Awaiting approval for compliance_audit", level="WARN")
                    self.security.request_approval(
                        capability="compliance_audit",
                        reason=f"Run scikit-learn IsolationForest & ECOD anomaly detection on {county} disbursements.",
                        agent="silent_auditor"
                    )
                    raise PermissionError(f"Capability 'compliance_audit' required but not granted. Approval request created.")
                
                # Record action once granted
                self.security.record_action("compliance_audit", {"county": county, "source": source_file})

        pd, load_data, timeseries_anomalies, crosssection_anomalies = _load_audit_pipeline()

        if not source_file:
            source_file = "/root/.openclaw/workspace/gateway_disbursements_2023.txt"

        source_path = Path(source_file)
        if not source_path.exists():
            raise FileNotFoundError(f"Disbursement source file not found at {source_file}")

        # Load and filter raw data for the specific county (case-insensitive)
        df_all = load_data(str(source_path))
        
        # In gateway_disbursements_2023.txt county names are like 'Adams', 'Pike'
        # In df_all we mapped cnty_description to county
        df_county = df_all[df_all['county'].astype(str).str.lower() == county.lower()]
        
        total_records = len(df_county)
        if total_records == 0:
            msg = f"No disbursement records found for county '{county}' in {source_file}."
            if self.session:
                self.session.log(msg, level="WARN")
            return CompliancePackage(
                county=county,
                summary=msg,
                total_records_audited=0,
                source_file=str(source_path),
            )

        # Run detectors (Timeseries and Cross-sectional)
        df_county_clean = df_county[df_county['amount'] >= 0]
        
        ts_anom = timeseries_anomalies(df_county_clean, min_years=2) # default to min 2 years for filtered sets
        cs_anom = crosssection_anomalies(df_county_clean)

        # Combine results
        combined_anom = pd.concat([ts_anom, cs_anom], ignore_index=True)
        if not combined_anom.empty:
            combined_anom = combined_anom.sort_values('score', ascending=False)

        # Limit to top anomalies for report clarity (e.g. top 25)
        top_anom = combined_anom.head(25)

        red_flags: list[RedFlag] = []
        for _, r in top_anom.iterrows():
            severity = "high" if float(r.get('score', 0)) > 20 else ("medium" if float(r.get('score', 0)) > 5 else "low")
            
            # Format display note
            cat = r.get('category')
            cat_str = f" / {cat}" if cat and not pd.isna(cat) else ""
            desc = f"Anomaly in {r.get('department')}{cat_str} (FY {r.get('fiscal_year')}). Amount: ${r.get('amount'):,.2f}."
            evidence = f"Flagged by {r.get('method')} with score {r.get('score'):.2f}. Note: {r.get('note')}."
            
            red_flags.append(
                RedFlag(
                    severity=severity,
                    category="budget_anomaly",
                    description=desc,
                    evidence=evidence,
                    recommended_action="Conduct a detailed ledger review of vendor payments for this department."
                )
            )

        overall_risk = min(10.0, 1.0 + len(red_flags) * 0.8)
        summary = (
            f"Silent Auditor completed compliance audit for {county} County. "
            f"Audited {total_records:,} line items in {source_path.name}. "
            f"Surfaced {len(red_flags)} anomalies with risk score of {overall_risk:.1f}/10."
        )

        pkg = CompliancePackage(
            county=county,
            red_flags=red_flags,
            overall_risk_score=round(overall_risk, 1),
            summary=summary,
            source_file=str(source_path),
            total_records_audited=total_records,
        )

        if self.session:
            self.session.write_handoff("silent_auditor", pkg)
            self.session.log(f"Silent Auditor audit complete. Found {len(red_flags)} flags.")

        return pkg
