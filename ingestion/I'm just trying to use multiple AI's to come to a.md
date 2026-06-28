<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# I'm just trying to use multiple AI's to come to a consensus....so...if  you have it figured out, give me one final instruction report and I will hand it straight to openclaw.

Here’s a single, self‑contained instruction report you can hand to OpenClaw / Grok‑Build as “the source of truth” for what to do next. It assumes the current ReClaw‑2.0 repo state (core/handoff models, agents, silent_auditor SOUL, sucker_pilot, etc.).[^1]

***

# ReClaw 2.0 – Silent Auditor \& Content Pipeline Upgrade Brief

## 0. Non‑negotiable constraints

Before making any changes, obey these rules:

1. **File‑based contracts only**
    - Agents communicate **only via JSON files on disk**, using Pydantic models defined in `core/handoff.py`.
    - Never rely on Python objects crossing agent boundaries.
2. **Do not break existing models**
    - `ResearchPackage`, `Insight`, `RedFlag`, `AnalysisPackage`, `ContentPackage`, `ForgePackage`, `AgentEvent` **already exist** in `core/handoff.py`.
    - You may **add** models and **append** fields, but you must not remove or rename existing fields or change their semantics.
3. **Keep Obsidian behavior intact**
    - Final artifacts are written as Markdown into `/root/obsidian_vault` (or equivalent) and especially under `Rural Data/`.[^1]
    - `core/obsidian_writer.py` and `ContentPackage.to_obsidian_frontmatter()` must continue to work as‑is.
4. **Respect session isolation**
    - All new files must live under `data/sessions/<id>/...` (sources, handoffs), as managed by `core/session.py` and the Gateway.

***

## 1. Core handoff extensions (core/handoff.py)

Goal: extend the central handoff models to support the Silent Auditor output and short‑form scripts, **without breaking anything existing**.

### 1.1 Add CompliancePackage

In `core/handoff.py`, **after** the existing `RedFlag` class, add:

```python
class CompliancePackage(BaseModel):
    """
    Output of Silent Auditor.
    Structured summary of rule-based checks across domains.
    """
    id: str = Field(default_factory=lambda: f"compliance-{uuid4().hex[:12]}")
    county: str
    state: str = "IN"
    year: int
    generated_at: datetime = Field(default_factory=now_utc)
    red_flags: list[RedFlag] = Field(default_factory=list)
    domains_covered: list[str] = Field(default_factory=list)  # ["procurement", "payroll", ...]
    overall_risk_score: float = Field(ge=0.0, le=10.0, default=3.0)
    notes: str = ""
```

Notes:

- Reuse the existing `uuid4` import and `now_utc()` helper already defined at the top of this file.
- Use the existing `RedFlag` model unchanged (fields: `severity`, `category`, `description`, `evidence`, `recommended_action`). Do **not** add `rule_id` or `meta` to `RedFlag` at this time.


### 1.2 Add ShortScript and extend ContentPackage

Still in `core/handoff.py`, **before** `ContentPackage`, add:

```python
class ShortScript(BaseModel):
    """
    One short-form video idea: hook + script + title.
    """
    slug: str
    platform: Literal["tiktok", "shorts", "reels"] = "shorts"
    title: str
    hook: str
    script: str  # 30–60s spoken text
    call_to_action: str | None = None
```

Then extend the existing `ContentPackage` class by **appending** one field at the bottom of the model (do not remove or reorder existing fields):

```python
class ContentPackage(BaseModel):
    # ...existing fields...
    short_scripts: list[ShortScript] = Field(default_factory=list)
```

- Preserve existing fields: `county`, `primary_area`, `generated_at`, `research`, `analysis`, `obsidian_filename`, `tags`, `video_title_ideas`, `key_stats`, and the `to_obsidian_frontmatter` method.

***

## 2. Indiana Gateway tool (tools/indiana_gateway.py)

Goal: refactor the existing Indiana Gateway logic in `agents/silent_auditor/sucker_pilot.py` into a reusable tool module.

### 2.1 Create tool module

Create a new file `tools/indiana_gateway.py` with:

```python
from pathlib import Path
import requests
from bs4 import BeautifulSoup

URL = "https://gateway.ifionline.org/public/download.aspx"

def download_disbursements(year: int, target_path: Path) -> Path:
    """
    Download the Indiana Gateway 'Disbursements by Fund' flat file
    for the given year and save it to target_path.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    response = session.get(URL, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Use the actual field names from your current working sucker_pilot.py.
    # Do NOT invent new ones; copy existing payload keys and adjust only if needed.[cite:52]
    viewstate = soup.find("input", {"id": "__VIEWSTATE"})["value"]
    viewstate_gen = soup.find("input", {"id": "__VIEWSTATEGENERATOR"})["value"]
    event_validation = soup.find("input", {"id": "__EVENTVALIDATION"})["value"]

    payload = {
        "__VIEWSTATE": viewstate,
        "__VIEWSTATEGENERATOR": viewstate_gen,
        "__EVENTVALIDATION": event_validation,
        # Use the same combo you currently use for "Annual Financial Reports" -> "Disbursements by Fund"[cite:52]
        "ctl00$ContentPlaceHolder1$RadComboBox1": "Annual Financial Reports",
        "ctl00$ContentPlaceHolder1$RadComboBox2": "Disbursements by Fund",
        "ctl00$ContentPlaceHolder1$DropDownListUnitType": "All",
        "ctl00$ContentPlaceHolder1$DropDownListYear": str(year),
        "ctl00$ContentPlaceHolder1$button_download1": "Download",
    }

    headers = {
        "User-Agent": "ReClaw-2.0",
        "Referer": URL,
    }

    res = session.post(URL, data=payload, headers=headers, timeout=60)
    res.raise_for_status()
    target_path.write_bytes(res.content)
    return target_path
```

Important:

- Base the payload keys and form fields on your **existing working** `sucker_pilot.py`, not on guesses.
- Don’t change delimiter assumptions here; this tool only downloads raw content.

***

## 3. Researcher integration (agents/researcher.py)

Goal: when targeting Indiana, the Researcher must:

- Download the Gateway disbursement file for a given year into `session/sources/gateway_disbursements_<year>.txt`.
- Add a `SourceRef` pointing to it in `ResearchPackage.sources`.
- Still write `handoffs/research.json` as a valid `ResearchPackage`.


### 3.1 Wire in Gateway download

In `agents/researcher.py`:

- Import the new tool and handoff models:

```python
from pathlib import Path
from core.handoff import ResearchPackage, SourceRef
from tools.indiana_gateway import download_disbursements
```

- In your main research function (whatever currently returns a `ResearchPackage` and writes `handoffs/research.json`), add logic similar to:

```python
def run_research(session_path: Path, county: str, primary_area: str, state: str = "IN", year: int = 2023) -> ResearchPackage:
    pkg = ResearchPackage(
        county=county,
        primary_area=primary_area,
        state=state,
    )

    # Existing seed/live fetch logic goes here...

    if state.upper() == "IN":
        src_name = f"gateway_disbursements_{year}.txt"
        dst = session_path / "sources" / src_name

        try:
            print(f"[Researcher] Downloading Indiana Gateway disbursements {year}...")
            download_disbursements(year, dst)
            pkg.sources.append(
                SourceRef(
                    kind="web",
                    url="https://gateway.ifionline.org/public/AFR.aspx",
                    note=f"Disbursements by Fund {year}, stored at sources/{src_name}",
                )
            )
        except Exception as e:
            print(f"[Researcher] Gateway download failed: {e}. Continuing with other sources.")

    # ...continue collecting property_records, budgets, salaries, summary, etc.[cite:79]

    handoffs = session_path / "handoffs"
    handoffs.mkdir(parents=True, exist_ok=True)
    (handoffs / "research.json").write_text(pkg.model_dump_json(indent=2))
    return pkg
```

Notes:

- Do **not** add a `year` field to `ResearchPackage`; keep it as‑is.
- Always include `primary_area` when constructing `ResearchPackage`.

***

## 4. Silent Auditor implementation (agents/silent_auditor)

Goal: turn the Silent Auditor from just a SOUL + pilot script into a real agent that:

- Reads `research.json`.
- Reads Gateway disbursement file.
- Loads `RULEBOOK.yml`.
- Produces a `CompliancePackage` (`compliance.json`).


### 4.1 RULEBOOK

Create `agents/silent_auditor/RULEBOOK.yml`:

```yaml
domains:
  procurement:
    rules:
      - id: SPLIT_PURCHASE
        severity: high
        description: Purchases split to avoid bid thresholds
        data_source: gateway_disbursements
        params:
          window_days: 30
          min_combined_amount: 50000
          single_tx_max: 49999
  claims:
    rules: []
  payroll:
    rules: []
  revenues:
    rules: []
  grants:
    rules: []
  transparency:
    rules: []
  control_environment:
    rules: []
```

This is a configuration file only. It must not hard‑code assumptions the code doesn’t match.

### 4.2 silent_auditor.py

Create `agents/silent_auditor/silent_auditor.py`:

```python
from pathlib import Path
import json
import yaml
import pandas as pd

from core.handoff import ResearchPackage, RedFlag, CompliancePackage

def run_silent_auditor(session_path: Path, year: int, county_name: str) -> CompliancePackage:
    research_path = session_path / "handoffs" / "research.json"
    rulebook_path = Path(__file__).parent / "RULEBOOK.yml"

    if not research_path.exists():
        raise FileNotFoundError(f"Missing ResearchPackage at {research_path}")

    research_pkg = ResearchPackage.model_validate_json(research_path.read_text())

    rulebook = yaml.safe_load(rulebook_path.read_text())
    red_flags: list[RedFlag] = []
    domains_processed: list[str] = []

    # Find Gateway source
    gateway_src = next(
        (s for s in research_pkg.sources if "gateway_disbursements" in (s.note or "")),
        None,
    )

    if gateway_src:
        domains_processed.append("procurement")
        data_file = session_path / "sources" / f"gateway_disbursements_{year}.txt"
        if data_file.exists():
            try:
                # Use the real delimiter your file uses; your original pilot used '|'.[cite:52]
                df = pd.read_csv(data_file, sep="|", on_bad_lines="skip", low_memory=False)

                # TODO: adapt these column names to actual columns in the file.
                # For now, guard each access and fail gracefully.
                if {"County", "Vendor", "Date", "Amount"}.issubset(df.columns):
                    df_local = df[df["County"].str.contains(county_name, case=False, na=False)].copy()
                    if not df_local.empty:
                        _apply_split_purchase_rule(df_local, rulebook, red_flags, county_name, year)
            except Exception as e:
                print(f"[SilentAuditor] Procurement rule evaluation error: {e}")

    if not red_flags:
        red_flags.append(
            RedFlag(
                severity="low",
                category="general",
                description=f"Baseline scan completed for {county_name} County. No high-risk anomalies found with current rules.",
                evidence=f"Checked Gateway disbursements {year} and available research sources.",
                recommended_action="Expand rulebook and add more data sources for deeper audits.",
            )
        )

    base_score = 2.0
    for flag in red_flags:
        if flag.severity == "high":
            base_score += 1.5
        elif flag.severity == "medium":
            base_score += 0.7
    risk_score = min(base_score, 10.0)

    pkg = CompliancePackage(
        county=county_name,
        state="IN",
        year=year,
        red_flags=red_flags,
        domains_covered=domains_processed or ["general"],
        overall_risk_score=round(risk_score, 1),
        notes=f"Forensic scan completed for {county_name} County.",
    )

    out_path = session_path / "handoffs" / "compliance.json"
    out_path.write_text(pkg.model_dump_json(indent=2))
    return pkg


def _apply_split_purchase_rule(df_local, rulebook, red_flags, county_name: str, year: int) -> None:
    proc_rules = rulebook["domains"]["procurement"]["rules"]
    rule = next((r for r in proc_rules if r["id"] == "SPLIT_PURCHASE"), None)
    if not rule:
        return

    params = rule["params"]
    window_days = params["window_days"]
    min_combined = params["min_combined_amount"]
    single_max = params["single_tx_max"]

    df_local["Date"] = pd.to_datetime(df_local["Date"], errors="coerce")
    df_local["Amount"] = pd.to_numeric(df_local["Amount"], errors="coerce")

    for vendor, group in df_local.groupby("Vendor"):
        g = group.dropna(subset=["Date", "Amount"]).sort_values("Date")
        for i in range(len(g) - 1):
            r1 = g.iloc[i]
            r2 = g.iloc[i + 1]
            days = (r2["Date"] - r1["Date"]).days
            combined = (r1["Amount"] or 0) + (r2["Amount"] or 0)

            if 0 <= days <= window_days and combined >= min_combined:
                if (r1["Amount"] < single_max) and (r2["Amount"] < single_max):
                    red_flags.append(
                        RedFlag(
                            severity="high",
                            category="procurement",
                            description=(
                                f"Potential split purchase for vendor '{vendor}' in {county_name} County: "
                                f"{r1['Amount']:.2f} on {r1['Date'].date()} and "
                                f"{r2['Amount']:.2f} on {r2['Date'].date()} "
                                f"total {combined:.2f}, near or above bidding threshold."
                            ),
                            evidence=(
                                f"Source: Indiana Gateway 'Disbursements by Fund' {year} file; "
                                f"two transactions within {days} days."
                            ),
                            recommended_action="Review procurement policy, bids, and approvals for this vendor.",
                        )
                    )
                    break
```

Later we can refine the column names using a real Gateway sample; this is designed to fail gracefully if the schema doesn’t match.

***

## 5. Content Studio: scripts from red flags (agents/content_studio)

Goal: build a minimal Content Studio agent that:

- Reads `analysis.json` (if present) and `compliance.json`.
- Collects red flags.
- Creates 1–3 `ShortScript`s and a list of `video_title_ideas`.
- Writes a `ContentPackage` JSON into `handoffs/content.json` using the **existing** ContentPackage structure plus `short_scripts`.

Create `agents/content_studio/content_studio.py`:

```python
from pathlib import Path
import json

from core.handoff import (
    ResearchPackage,
    AnalysisPackage,
    CompliancePackage,
    ContentPackage,
    ShortScript,
)

def run_content_studio(session_path: Path) -> ContentPackage:
    research_path = session_path / "handoffs" / "research.json"
    analysis_path = session_path / "handoffs" / "analysis.json"
    compliance_path = session_path / "handoffs" / "compliance.json"

    research = ResearchPackage.model_validate_json(research_path.read_text()) if research_path.exists() else None
    analysis = AnalysisPackage.model_validate_json(analysis_path.read_text()) if analysis_path.exists() else None
    compliance = CompliancePackage.model_validate_json(compliance_path.read_text()) if compliance_path.exists() else None

    county = analysis.county if analysis else (compliance.county if compliance else "Unknown")
    primary_area = analysis.primary_area if analysis else research.primary_area if research else "General"

    flags = []
    if compliance:
        flags.extend(compliance.red_flags)
    if analysis:
        flags.extend(analysis.red_flags)

    high = [f for f in flags if f.severity == "high"]
    targets = high or flags

    scripts: list[ShortScript] = []
    titles: list[str] = []

    for idx, flag in enumerate(targets[:3]):
        slug = f"{county.lower().replace(' ', '-')}-flag-{idx+1}"
        title = f"{county} County: {flag.category.capitalize()} red flag"
        hook = f\"\"\"If you live in {county} County, you should see this.\"\"\"
        script = (
            f"{hook} "
            f"{flag.description} "
            f"This comes straight from public records, not rumors. "
            f"If you care how your tax money is used, this is worth a closer look."
        )
        cta = f"If you're in {county}, save this and share it with someone who lives here."

        s = ShortScript(
            slug=slug,
            platform="shorts",
            title=title,
            hook=hook,
            script=script,
            call_to_action=cta,
        )
        scripts.append(s)
        titles.append(title)

    content = ContentPackage(
        county=county,
        primary_area=primary_area,
        research=research,
        analysis=analysis,
        video_title_ideas=titles,
        short_scripts=scripts,
    )

    out_path = session_path / "handoffs" / "content.json"
    out_path.write_text(content.model_dump_json(indent=2))
    return content
```


***

## 6. AGENTS.md routing and pipeline order (docs only)

Update `AGENTS.md` to reflect the new agents and sequence.

Add:

```markdown
### silent_auditor

- **SOUL:** agents/silent_auditor/SOUL.md
- **Mission:** Deep compliance and red-flag audit of county disbursements, salaries, and property records for rural IN.
- **Inputs:** ResearchPackage JSON at session/handoffs/research.json + source files in session/sources/.
- **Outputs:** CompliancePackage JSON at session/handoffs/compliance.json.
- **Permissions:** Read session/sources/* and session/handoffs/research.json; write only session/handoffs/compliance.json.
- **Routing:** Runs after `researcher` in full runs when state == IN.

### content_studio

- **SOUL:** agents/content_studio/SOUL.md (to be created later if needed)
- **Mission:** Turn top red flags into short-form video scripts for TikTok/YouTube Shorts.
- **Inputs:** AnalysisPackage (session/handoffs/analysis.json) and CompliancePackage (session/handoffs/compliance.json).
- **Outputs:** ContentPackage with short_scripts at session/handoffs/content.json.
- **Permissions:** Read handoffs/{research,analysis,compliance}.json; write handoffs/content.json.
- **Routing:** Runs after `analyst` and `silent_auditor`.
```

And document the full pipeline:

```markdown
Pipeline (full rural_data cycle, Indiana):

researcher → silent_auditor → analyst → content_studio → orchestrator → obsidian_writer
```

(Or, if you want Analyst before Auditor, adjust order accordingly.)

***

## 7. CLI / testing instructions

Finally, wire or document a simple CLI path (you can update `cli.py` or just use Python entrypoints):

- For Pike research only:

```bash
python -m reclaw.cli run --county "Pike" --area "Winslow" --year 2023 --mode research-only
```

Expected:

- `data/sessions/<id>/sources/gateway_disbursements_2023.txt` exists.
- `data/sessions/<id>/handoffs/research.json` has a `SourceRef` pointing to it.
- For full chain (once you’ve wired the calls):

```bash
python -m reclaw.cli run --county "Pike" --area "Winslow" --year 2023 --mode full
```

Expected (same session):

- `handoffs/research.json` – `ResearchPackage`.
- `handoffs/compliance.json` – `CompliancePackage` from Silent Auditor.
- `handoffs/analysis.json` – existing Analyst output.
- `handoffs/content.json` – `ContentPackage` with `short_scripts`.
- Obsidian vault updated by orchestrator/obsidian_writer as before.[^1]

***

Give this document to OpenClaw / Grok‑Build and tell it:

> “Implement exactly this brief against the ReClaw‑2.0 repo. Do not change any existing model signatures besides the explicit extensions above, and keep everything file‑based. Start with Pike County, IN, 2023 as the primary test case.”

That should be enough for it to “cook” without guessing.

<div align="center">⁂</div>

[^1]: https://www.perplexity.ai/search/04382e90-6e56-431b-9636-0f5c42b7a8f7

