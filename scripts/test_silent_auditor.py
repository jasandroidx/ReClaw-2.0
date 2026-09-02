#!/usr/bin/env python3
"""
Test script for SilentAuditorAgent.
Runs inside ReClaw-2.0 directory structure.
"""

import sys
from pathlib import Path

# Add root of ReClaw-2.0 to path
sys.path.append(str(Path(__file__).parent.parent))

from core.session import create_session
from core.security import SecurityManager
from agents.silent_auditor import SilentAuditorAgent


def test_silent_auditor():
    print("=== Testing Silent Auditor Agent ===")
    
    # 1. Create a session
    session, task = create_session(
        county="Adams",
        area="Decatur",
        triggered_by="test_script",
        auto_approve=False,
        write_to_obsidian=False
    )
    print(f"Created isolated session: {session.session_id} at {session.base_dir}")

    # 2. Instantiate the agent
    agent = SilentAuditorAgent(session=session)

    # 3. Test Gated Path (should raise PermissionError since 'compliance_audit' is not granted)
    print("\n--- Testing Gated Path (No Grant) ---")
    try:
        agent.run(county="Adams")
        print("FAIL: Managed to run without capability grant!")
    except PermissionError as e:
        print(f"PASS: Raised expected PermissionError: {e}")
        
        # Verify approval request was written to disk
        sec = SecurityManager(session.base_dir, session.session_id)
        requests = sec.get_pending_requests()
        print(f"Pending requests: {len(requests)}")
        for r in requests:
            print(f"  - Request ID: {r.id}, Capability: {r.capability}, Agent: {r.requested_by}, Reason: {r.reason}")

    # 4. Test Approved Path (pre-grant capability)
    print("\n--- Testing Approved Path (With Grant) ---")
    sec = SecurityManager(session.base_dir, session.session_id)
    sec.grant("compliance_audit", granted_by="test_harness", notes="Pre-granting for verification")
    print("Granted capability: 'compliance_audit'")

    # Recreate agent to load the new grant from disk
    agent = SilentAuditorAgent(session=session)

    # Run for Adams county
    try:
        pkg = agent.run(county="Adams")
        print("PASS: Run completed successfully after grant!")
        print(f"Compliance Report for {pkg.county}:")
        print(f"  - Total records audited: {pkg.total_records_audited}")
        print(f"  - Overall risk score: {pkg.overall_risk_score}/10")
        print(f"  - Red flags found: {len(pkg.red_flags)}")
        print(f"  - Summary: {pkg.summary}")
        
        # Print top 3 red flags
        print("Top 3 anomalies:")
        for idx, flag in enumerate(pkg.red_flags[:3], 1):
            print(f"    {idx}. [{flag.severity.upper()}] {flag.description}")
            print(f"       Evidence: {flag.evidence}")
    except Exception as e:
        print(f"FAIL: Run failed with error: {e}")
        import traceback
        traceback.print_exc()

    # Run for Pike county (testing no records case or what is available)
    print("\n--- Testing Pike County (Seed / Disbursements) ---")
    try:
        # Pike county checks
        pkg_pike = agent.run(county="Pike")
        print(f"Compliance Report for {pkg_pike.county}:")
        print(f"  - Total records audited: {pkg_pike.total_records_audited}")
        print(f"  - Overall risk score: {pkg_pike.overall_risk_score}/10")
        print(f"  - Red flags found: {len(pkg_pike.red_flags)}")
        print(f"  - Summary: {pkg_pike.summary}")
    except Exception as e:
        print(f"FAIL: Pike run failed: {e}")

    print("\n=== Silent Auditor Verification Completed ===")


if __name__ == "__main__":
    test_silent_auditor()
