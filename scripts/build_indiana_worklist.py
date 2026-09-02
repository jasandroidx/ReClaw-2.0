#!/usr/bin/env python3
"""Build Indiana county worklist ordered outward from Pike (gateway codes + FIPS + geo)."""
from __future__ import annotations

import csv
import json
import math
from io import StringIO
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
CACHE = REPO / "data" / "cache" / "gateway_disbursements_2024.txt"
OUT = REPO / "data" / "indiana_county_worklist.yaml"

# Pike County centroid (Petersburg) — sort key
PIKE_LAT, PIKE_LON = 38.019, -87.285

# County seat approximations (lat, lon) for distance ordering — Indiana 92 counties
COUNTY_GEO: dict[str, tuple[float, float]] = {
    "Adams": (40.745, -84.936),
    "Allen": (41.130, -85.130),
    "Bartholomew": (39.201, -85.921),
    "Benton": (40.606, -87.311),
    "Blackford": (40.520, -85.325),
    "Boone": (40.050, -86.469),
    "Brown": (39.145, -86.230),
    "Carroll": (40.583, -86.563),
    "Cass": (40.753, -86.348),
    "Clark": (38.308, -85.760),
    "Clay": (39.396, -87.110),
    "Clinton": (40.301, -86.475),
    "Crawford": (38.290, -86.458),
    "Daviess": (38.695, -87.075),
    "Dearborn": (39.145, -84.973),
    "Decatur": (39.307, -85.501),
    "DeKalb": (41.396, -85.055),
    "Delaware": (40.193, -85.396),
    "Dubois": (38.376, -86.874),
    "Elkhart": (41.594, -85.858),
    "Fayette": (39.640, -85.180),
    "Floyd": (38.315, -85.906),
    "Fountain": (40.120, -87.243),
    "Franklin": (39.415, -85.060),
    "Fulton": (41.322, -86.263),
    "Gibson": (38.305, -87.571),
    "Grant": (40.515, -85.650),
    "Greene": (39.035, -87.045),
    "Hamilton": (40.045, -86.052),
    "Hancock": (39.783, -85.773),
    "Harrison": (38.195, -86.110),
    "Hendricks": (39.641, -86.515),
    "Henry": (39.931, -85.396),
    "Howard": (40.483, -86.114),
    "Huntington": (40.880, -85.490),
    "Jackson": (38.907, -86.038),
    "Jasper": (41.019, -87.120),
    "Jay": (40.438, -85.006),
    "Jefferson": (38.790, -85.430),
    "Jennings": (39.018, -85.630),
    "Johnson": (39.423, -86.055),
    "Knox": (38.678, -87.420),
    "Kosciusko": (41.291, -85.860),
    "LaGrange": (41.645, -85.420),
    "Lake": (41.474, -87.349),
    "LaPorte": (41.607, -86.722),
    "Lawrence": (38.830, -86.485),
    "Madison": (40.105, -85.680),
    "Marion": (39.768, -86.158),
    "Marshall": (41.325, -86.260),
    "Martin": (38.731, -86.803),
    "Miami": (40.762, -86.060),
    "Monroe": (39.165, -86.523),
    "Montgomery": (40.040, -86.860),
    "Morgan": (39.481, -86.445),
    "Newton": (40.990, -87.150),
    "Noble": (41.396, -85.420),
    "Ohio": (38.785, -84.965),
    "Orange": (38.545, -86.495),
    "Owen": (39.307, -86.838),
    "Parke": (39.760, -87.205),
    "Perry": (38.080, -86.645),
    "Pike": (38.019, -87.285),
    "Porter": (41.478, -87.069),
    "Posey": (38.020, -87.785),
    "Pulaski": (41.045, -86.635),
    "Putnam": (39.575, -86.850),
    "Randolph": (40.170, -85.010),
    "Ripley": (39.103, -85.265),
    "Rush": (39.620, -85.470),
    "St. Joseph": (41.616, -86.290),
    "Scott": (38.685, -85.745),
    "Shelby": (39.520, -85.790),
    "Spencer": (38.017, -87.000),
    "Starke": (41.280, -86.650),
    "Steuben": (41.643, -85.000),
    "Sullivan": (39.090, -87.415),
    "Switzerland": (38.825, -85.025),
    "Tippecanoe": (40.417, -86.875),
    "Tipton": (40.280, -86.040),
    "Union": (39.625, -84.925),
    "Vanderburgh": (38.020, -87.570),
    "Vermillion": (39.760, -87.460),
    "Vigo": (39.427, -87.391),
    "Wabash": (40.838, -85.795),
    "Warren": (40.350, -87.350),
    "Warrick": (38.099, -87.274),
    "Washington": (38.600, -86.105),
    "Wayne": (39.865, -85.010),
    "Wells": (40.730, -85.220),
    "White": (40.750, -86.865),
    "Whitley": (41.140, -85.490),
}


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 3959  # miles
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _gateway_counties() -> dict[int, str]:
    if not CACHE.exists():
        raise FileNotFoundError(f"Missing {CACHE} — run scripts/prefetch_gateway_years.sh")
    raw = CACHE.read_text()
    rdr = csv.DictReader(StringIO(raw), delimiter="|")
    uniq: dict[int, str] = {}
    for row in rdr:
        cd = row.get("cnty_cd", "").strip()
        name = row.get("cnty_description", "").strip()
        if cd and name:
            uniq[int(cd)] = name
    return uniq


def _fips(gateway_code: int) -> str:
    """Indiana county FIPS: alphabetical gateway code → 18{odd 3-digit}."""
    return f"18{2 * gateway_code - 1:03d}"


def build() -> list[dict]:
    gw = _gateway_counties()
    rows = []
    for code, name in gw.items():
        lat, lon = COUNTY_GEO.get(name, (39.85, -86.25))
        dist = _haversine(PIKE_LAT, PIKE_LON, lat, lon)
        rows.append(
            {
                "gateway_code": code,
                "name": name,
                "fips": _fips(code),
                "state": "IN",
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "distance_from_pike_mi": round(dist, 1),
                "county_seat_hint": f"{name} County, IN",
                "geo_push": (
                    f"Facebook: '{name} County News', local town groups, "
                    f"#{name.replace(' ', '')}Indiana #IndianaTaxpayers"
                ),
            }
        )
    # Pike first, then nearest neighbors outward
    rows.sort(key=lambda r: (0 if r["name"] == "Pike" else 1, r["distance_from_pike_mi"]))
    for i, r in enumerate(rows):
        r["worklist_position"] = i
    return rows


def main() -> None:
    rows = build()
    payload = {
        "generated_from": str(CACHE),
        "anchor": "Pike",
        "total_counties": len(rows),
        "counties": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"Wrote {len(rows)} counties → {OUT}")
    print("First 8:", [r["name"] for r in rows[:8]])


if __name__ == "__main__":
    main()