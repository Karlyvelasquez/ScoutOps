#!/usr/bin/env python3
"""Quick test to validate confidence score fixes."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agent.graph import run_triage_agent
from agent.schemas.input_schema import IncidentReport

TEST_CASES = [
    {
        "name": "Checkout Failure (P1) - Should be HIGH confidence",
        "report": IncidentReport(
            source="QA",
            description="Users are getting 'Payment declined' errors when trying to complete checkout with Stripe. The error appears after clicking 'Pay Now' button. This started happening 30 minutes ago. Multiple users reporting in #incidents channel. Transaction logs show Stripe API returning 402 status code.",
            reporter_email="ops@company.com",
        ),
        "min_confidence": 0.75,
    },
    {
        "name": "Login Error (P2) - Should be HIGH confidence",
        "report": IncidentReport(
            source="soporte",
            description="Customers unable to login. Getting 'Invalid credentials' error even with correct password. Session tokens not being generated. Issue started after deployment at 2:15 AM. Affects all users, not just specific accounts.",
            reporter_email="support@company.com",
        ),
        "min_confidence": 0.75,
    },
    {
        "name": "Catalog Search Issue (P2) - Should be HIGH confidence",
        "report": IncidentReport(
            source="QA",
            description="Product search is returning no results for any query. The search endpoint is responding with 500 errors. Product listing page works fine but search feature is completely broken. This is blocking customer ability to find products.",
            reporter_email="dev@company.com",
        ),
        "min_confidence": 0.75,
    },
    {
        "name": "Cart Items Not Persisting (P2) - Should be HIGH confidence",
        "report": IncidentReport(
            source="QA",
            description="Items not persisting in shopping cart. When users add products to cart and refresh the page, items disappear. Cart API endpoint /graphql returning null for cart query. Database queries show items are being inserted but not retrieved.",
            reporter_email="ops@company.com",
        ),
        "min_confidence": 0.75,
    },
    {
        "name": "Inventory Stock Not Updating (P3) - Should be MODERATE confidence",
        "report": IncidentReport(
            source="soporte",
            description="Stock levels not updating correctly. When orders are placed, inventory counts are not decreasing. Backorder system is not triggering notifications. This is causing overselling of out-of-stock items.",
            reporter_email="inventory@company.com",
        ),
        "min_confidence": 0.70,
    },
    {
        "name": "Shipping Rate Calculation Broken (P3) - Should be MODERATE confidence",
        "report": IncidentReport(
            source="soporte",
            description="Shipping rate calculation is broken. Customers see incorrect shipping costs at checkout. Some regions showing $0 shipping, others showing $999. The shipping provider integration with FedEx API seems to be failing silently.",
            reporter_email="fulfillment@company.com",
        ),
        "min_confidence": 0.70,
    },
    {
        "name": "Performance Degradation (P2) - Should be HIGH confidence",
        "report": IncidentReport(
            source="monitoring",
            description="API response times degraded significantly. GraphQL queries taking 5-10 seconds instead of normal 200-500ms. Database queries are slow. CPU usage at 95%. This is affecting all endpoints across the platform.",
            reporter_email="sre@company.com",
        ),
        "min_confidence": 0.70,
    },
    {
        "name": "Vague/Ambiguous Report - Should be LOW confidence",
        "report": IncidentReport(
            source="soporte",
            description="Something is broken. Users are complaining. Not sure what the issue is exactly.",
            reporter_email="unknown@company.com",
        ),
        "min_confidence": 0.0,  # No minimum, just check it's low
        "max_confidence": 0.65,  # Should be below escalation threshold
    },
]


def main():
    print("=" * 80)
    print("CONFIDENCE SCORE FIX VALIDATION TEST")
    print("=" * 80)
    print()

    passed = 0
    failed = 0

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"[{i}/{len(TEST_CASES)}] {test_case['name']}")
        print("-" * 80)

        try:
            result = run_triage_agent(test_case["report"])

            confidence = result.confidence_score
            min_conf = test_case.get("min_confidence", 0.0)
            max_conf = test_case.get("max_confidence", 1.0)

            print(f"  Incident Type: {result.incident_type}")
            print(f"  Severity: {result.severity}")
            print(f"  Team: {result.assigned_team}")
            print(f"  Plugin: {result.affected_plugin}")
            print(f"  Confidence Score: {confidence}")

            # Validate confidence
            if confidence < min_conf:
                print(f"  ❌ FAILED: Confidence {confidence} < minimum {min_conf}")
                failed += 1
            elif confidence > max_conf:
                print(f"  ❌ FAILED: Confidence {confidence} > maximum {max_conf}")
                failed += 1
            else:
                print(f"  ✅ PASSED: Confidence {confidence} is in range [{min_conf}, {max_conf}]")
                passed += 1

        except Exception as e:
            print(f"  ❌ FAILED with exception: {e}")
            failed += 1

        print()

    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(TEST_CASES)} tests")
    print("=" * 80)

    if failed == 0:
        print("✅ All tests passed! Confidence fixes are working correctly.")
        return 0
    else:
        print(f"❌ {failed} test(s) failed. Review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
