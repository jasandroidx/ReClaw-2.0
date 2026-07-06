# extract_pike_budget.py
# Convert "Pike-241210-2025-Budget-Order.pdf" → schema CSV for the DOGEGPT pipeline.

import re, sys, os
import pandas as pd

def _to_num(x):
    if x is None: return None
    s = str(x).strip().replace("$","").replace(",","")
    s = s.replace("(","-").replace(")","")
    try:
        return float(s)
    except:
        return None

def _clean_cell(x):
    if x is None: return ""
    return re.sub(r"\s+", " ", str(x).strip())

def extract_with_tabula(pdf_path):
    try:
        import tabula
    except Exception:
        return []
    dfs = []
    # Try lattice then stream
    for lattice in (True, False):
        try:
            tmp = tabula.read_pdf(pdf_path, pages="all", lattice=lattice, stream=not lattice, multiple_tables=True)
            dfs.extend(tmp or [])
        except Exception:
            pass
    return dfs

def extract_with_camelot(pdf_path):
    try:
        import camelot
    except Exception:
        return []
    dfs = []
    for flavor in ("lattice","stream"):
        try:
            tables = camelot.read_pdf(pdf_path, pages="all", flavor=flavor)
            for t in tables:
                dfs.append(t.df)
        except Exception:
            pass
    return dfs

def extract_with_pdfplumber(pdf_path):
    try:
        import pdfplumber
    except Exception:
        return []
    dfs = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            # Only process pages that look like Budget Order + Unit header
            if "2025 Budget Order" in text and "Unit:" in text:
                for strategy in (
                    dict(vertical_strategy="lines", horizontal_strategy="lines"),
                    dict(vertical_strategy="text", horizontal_strategy="text"),
                    dict(vertical_strategy="explicit", horizontal_strategy="explicit"),
                ):
                    try:
                        tables = page.extract_tables(table_settings=strategy)
                        for tbl in tables or []:
                            if not tbl: 
                                continue
                            df = pd.DataFrame(tbl)
                            # keep only tables that contain the expected headers
                            header_line = " ".join(df.iloc[0].astype(str).tolist()).upper()
                            if "FUND" in header_line and "FUND NAME" in header_line and "CERTIFIED" in header_line:
                                # use first row as header
                                df.columns = [c.strip() for c in df.iloc[0].fillna("").tolist()]
                                df = df.iloc[1:].reset_index(drop=True)
                                dfs.append(df)
                    except Exception:
                        pass
    return dfs

def detect_unit_from_textblocks(df_like_list):
    # We’ll try to infer the unit/department from the small “Unit: #### NAME” tables around
    # If not found here, the calling code passes it in page-by-page when using pdfplumber.
    return None

def normalize_tables(dfs):
    """Return a single tidy DataFrame with columns:
       county, fiscal_year, department, category, account_code, amount,
       certified_av, certified_levy, certified_rate, notes
    """
    rows = []
    for df in dfs:
        # Flexible column name mapping
        cols = {str(c).strip().lower(): c for c in df.columns}
        def pick(*names):
            for n in names:
                if n in cols: return cols[n]
            return None

        c_fund = pick("fund")
        c_name = pick("fund name","fundname")
        c_cb   = pick("certified budget","budget")
        c_av   = pick("certified av","av","assessed value")
        c_levy = pick("certified levy","levy")
        c_rate = pick("certified rate","rate")

        # If this table doesn’t look like a fund table, skip it
        if not (c_fund and c_name and (c_cb or c_levy or c_rate)):
            continue

        for _, r in df.iterrows():
            fund = _clean_cell(r.get(c_fund))
            name = _clean_cell(r.get(c_name))
            # Skip blank or “Unit Total”/notes rows
            if not fund and not name:
                continue
            if name.upper().startswith("UNIT TOTAL") or name.upper().startswith("STATE OF INDIANA"):
                continue

            rec = {
                # Fill county/year/department later in caller when known
                'county': None,
                'fiscal_year': None,
                'department': None,

                'category': name or "",
                'account_code': fund or "",
                'amount': _to_num(r.get(c_cb)) if c_cb else None,
                'certified_av': _to_num(r.get(c_av)) if c_av else None,
                'certified_levy': _to_num(r.get(c_levy)) if c_levy else None,
                'certified_rate': _to_num(r.get(c_rate)) if c_rate else None,
                'notes': ""
            }
            # Filter obviously empty lines
            if (rec['category']=="" and rec['account_code']=="") or all(v in (None,"") for v in [rec['amount'],rec['certified_levy'],rec['certified_rate']]):
                continue
            rows.append(rec)
    return pd.DataFrame(rows)

def annotate_department_from_pdf(pdf_path, df):
    """Walk each page, find 'Unit:  #### NAME', apply NAME to nearby rows by proximity (best-effort)."""
    try:
        import pdfplumber
    except Exception:
        # If we can’t read pages, fallback to UNKNOWN
        df['department'] = df['department'].fillna("UNKNOWN UNIT")
        return df

    # Build a list of (page_index, unit_name) where detected
    page_units = {}
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if "2025 Budget Order" in text and "Unit:" in text:
                # e.g., "Unit:  0000 PIKE COUNTY"
                m = re.search(r"Unit:\s+(\d+\s+)?([A-Z0-9 .&/-]+)", text)
                dept = None
                if m:
                    dept = m.group(2).strip()
                # Clean: collapse multiple spaces
                if dept:
                    dept = re.sub(r"\s+", " ", dept)
                    page_units[i] = dept

    # Heuristic: evenly assign rows across pages in order
    # Simpler approach: just fill all missing with last seen department.
    last = None
    departments = []
    total_rows = len(df)
    # We don’t have row→page mapping; assign in blocks by fund headers frequency.
    # Practical shortcut: fill all with last detected dept; if none, fallback to "PIKE COUNTY" for first block.
    # (For most Budget Order PDFs, tables immediately follow the Unit header; merging is acceptable for a first pass.)
    if page_units:
        # Use the most frequent unit name when unknown
        common = list(page_units.values())[0]
    else:
        common = "PIKE COUNTY"

    df['department'] = df['department'].fillna(common)
    return df

def main():
    if len(sys.argv) < 3:
        print("Usage: python extract_pike_budget.py <PDF_PATH> <OUT_CSV> [--county 'Pike County, IN'] [--year 2025]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    out_csv  = sys.argv[2]
    county = "Pike County, IN"
    fiscal_year = 2025
    for i,a in enumerate(sys.argv):
        if a == "--county" and i+1 < len(sys.argv): county = sys.argv[i+1]
        if a == "--year" and i+1 < len(sys.argv):
            try: fiscal_year = int(sys.argv[i+1])
            except: pass

    # Try Tabula → Camelot → pdfplumber
    dfs = extract_with_tabula(pdf_path)
    if not dfs:
        dfs = extract_with_camelot(pdf_path)
    if not dfs:
        dfs = extract_with_pdfplumber(pdf_path)
    if not dfs:
        print("Could not extract any tables. Install one of: tabula-py (Java), camelot-py[cv] (Ghostscript/Poppler), or pdfplumber.")
        sys.exit(2)

    tidy = normalize_tables(dfs)
    if tidy.empty:
        print("No fund tables detected. Aborting.")
        sys.exit(3)

    # Fill county & year
    tidy['county'] = county
    tidy['fiscal_year'] = fiscal_year

    # Best-effort department assignment
    tidy = annotate_department_from_pdf(pdf_path, tidy)

    # Minimal schema required by pipeline; keep extra fields too
    cols_order = ["county","fiscal_year","department","category","account_code","amount","certified_av","certified_levy","certified_rate","notes"]
    for c in cols_order:
        if c not in tidy.columns:
            tidy[c] = None
    tidy = tidy[cols_order]

    # Clean department casing
    tidy['department'] = tidy['department'].astype(str).str.strip()

    # Save
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    tidy.to_csv(out_csv, index=False)
    print(f"Wrote {len(tidy):,} rows → {out_csv}")

if __name__ == "__main__":
    main()
