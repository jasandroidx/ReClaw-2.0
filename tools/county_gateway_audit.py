"""Gateway county audit — thin wrapper around tools.local_auditor_live."""

from __future__ import annotations

from tools.audit_adapter import AuditResult
from tools.local_auditor_live import audit_county


def audit_county_gateway(
    gateway_code: int,
    county_name: str,
    *,
    year: int = 2024,
    prior_year: int | None = 2023,
) -> AuditResult:
    _ = year, prior_year
    return audit_county(
        "IN",
        f"18{2 * gateway_code - 1:03d}",
        f"{county_name} County",
        gateway_code=gateway_code,
    )