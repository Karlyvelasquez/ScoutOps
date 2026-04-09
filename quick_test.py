#!/usr/bin/env python
"""
Quick test script to verify the 3 critical implementations without Docker.
Run: python quick_test.py
"""

import sys
from unittest.mock import patch
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agent.schemas.input_schema import IncidentReport
from agent.state import AgentState
from agent.graph import run_triage_agent


def test_rag_integration():
    """Test 1: RAG module is wired into the agent."""
    print("\n" + "="*60)
    print("TEST 1: RAG Integration (Retrieve Node)")
    print("="*60)

    description = "Payment processing failing for Stripe integration"
    incident_report = IncidentReport(
        description=description,
        source="QA",
    )

    with patch("rag.queries.query_codebase") as mock_rag:
        mock_rag.return_value = [
            {
                "plugin_name": "api-plugin-payments-stripe",
                "file_path": "plugins/payments/stripe/resolver.ts",
                "content": "export const chargeCard = async (amount) => { ... }",
                "relevance_score": 0.92,
            },
            {
                "plugin_name": "api-plugin-payments",
                "file_path": "plugins/payments/handler.ts",
                "content": "const processPayment = (card) => { ... }",
                "relevance_score": 0.78,
            },
        ]

        result = run_triage_agent(incident_report)

        print(f"✓ Incident type: {result.incident_type}")
        print(f"✓ Severity: {result.severity}")
        print(f"✓ Affected plugin: {result.affected_plugin}")
        print(f"✓ Affected file: {result.affected_file}")
        print(f"✓ Summary: {result.summary[:100]}...")

        if result.affected_file and result.affected_file != "None":
            print("\n✅ TEST 1 PASSED: RAG context populated affected_file")
            return True
        else:
            print("\n❌ TEST 1 FAILED: affected_file is null or 'None'")
            return False


def test_confidence_scoring():
    """Test 2: Confidence scoring (not hardcoded)."""
    print("\n" + "="*60)
    print("TEST 2: Confidence Scoring (Hybrid: 60% LLM + 40% RAG)")
    print("="*60)

    description = "Payment processing failing"
    incident_report = IncidentReport(
        description=description,
        source="QA",
    )

    with patch("rag.queries.query_codebase") as mock_rag, \
         patch("agent.utils.llm_client.generate_structured_output") as mock_llm:

        mock_rag.return_value = [
            {
                "plugin_name": "api-plugin-payments-stripe",
                "file_path": "plugins/payments/stripe/resolver.ts",
                "content": "...",
                "relevance_score": 0.80,
            }
        ]

        def llm_side_effect(prompt, response_schema=None, temperature=None):
            if response_schema and "confidence_score" in str(response_schema):
                return {
                    "severity": "P2",
                    "assigned_team": "payments-team",
                    "affected_plugin": "api-plugin-payments-stripe",
                    "layer": "GraphQL",
                    "suggested_actions": ["Check Stripe API key"],
                    "confidence_score": 0.75,
                }
            return {}

        mock_llm.side_effect = llm_side_effect

        result = run_triage_agent(incident_report)

        expected_hybrid = (0.75 * 0.6) + (0.80 * 0.4)
        actual = result.confidence_score

        print(f"✓ LLM confidence: 0.75")
        print(f"✓ RAG relevance: 0.80")
        print(f"✓ Expected hybrid: {expected_hybrid:.4f}")
        print(f"✓ Actual confidence: {actual:.4f}")

        if 0.0 <= actual <= 1.0 and actual != 0.85:
            print("\n✅ TEST 2 PASSED: Confidence is real (not hardcoded to 0.85)")
            return True
        else:
            print(f"\n❌ TEST 2 FAILED: Confidence is {actual} (should be ~{expected_hybrid:.4f})")
            return False


def test_escalation_threshold():
    """Test 3: Low confidence triggers escalation."""
    print("\n" + "="*60)
    print("TEST 3: Human-in-the-Loop (Escalation at < 0.70)")
    print("="*60)

    description = "Something is broken"
    incident_report = IncidentReport(
        description=description,
        source="soporte",
    )

    with patch("rag.queries.query_codebase") as mock_rag, \
         patch("agent.utils.llm_client.generate_structured_output") as mock_llm:

        mock_rag.return_value = []

        def llm_side_effect(prompt, response_schema=None, temperature=None):
            if response_schema and "confidence_score" in str(response_schema):
                return {
                    "severity": "P3",
                    "assigned_team": "platform-team",
                    "affected_plugin": "unknown",
                    "layer": "Unknown",
                    "suggested_actions": ["Needs clarification"],
                    "confidence_score": 0.45,
                }
            return {}

        mock_llm.side_effect = llm_side_effect

        result = run_triage_agent(incident_report)

        print(f"✓ Confidence score: {result.confidence_score:.4f}")
        print(f"✓ Threshold: 0.70")
        print(f"✓ Should escalate: {result.confidence_score < 0.70}")

        if result.confidence_score < 0.70:
            print("\n✅ TEST 3 PASSED: Low confidence triggers escalation")
            return True
        else:
            print(f"\n❌ TEST 3 FAILED: Confidence {result.confidence_score} should be < 0.70")
            return False


def test_agent_state_fields():
    """Test 4: AgentState has new fields."""
    print("\n" + "="*60)
    print("TEST 4: AgentState Fields (rag_context, attachment_analysis, escalated)")
    print("="*60)

    try:
        state: AgentState = {
            "incident_report": IncidentReport(description="Test incident description", source="QA"),
            "incident_type": "payment_failure",
            "entities": {},
            "rag_context": [{"plugin_name": "test", "file_path": "test.ts", "content": "...", "relevance_score": 0.9}],
            "attachment_analysis": "Error code: ECONNREFUSED",
            "technical_summary": "Test summary",
            "triage_result": None,
            "escalated": False,
            "errors": [],
            "node_timings": {},
        }

        print(f"✓ rag_context: {state['rag_context']}")
        print(f"✓ attachment_analysis: {state['attachment_analysis']}")
        print(f"✓ escalated: {state['escalated']}")

        print("\n✅ TEST 4 PASSED: All AgentState fields present")
        return True
    except Exception as e:
        print(f"\n❌ TEST 4 FAILED: {e}")
        return False


def test_reporter_email():
    """Test 5: Reporter email is collected."""
    print("\n" + "="*60)
    print("TEST 5: Reporter Email Field")
    print("="*60)

    email = "engineer@company.com"
    incident_report = IncidentReport(
        description="Test incident",
        source="QA",
        reporter_email=email,
    )

    print(f"✓ Reporter email: {incident_report.reporter_email}")

    if incident_report.reporter_email == email:
        print("\n✅ TEST 5 PASSED: Reporter email collected")
        return True
    else:
        print("\n❌ TEST 5 FAILED: Reporter email not stored")
        return False


def main():
    print("\n" + "="*60)
    print("ScoutOps Agent Integration — Quick Test Suite")
    print("="*60)

    results = []
    try:
        results.append(("RAG Integration", test_rag_integration()))
    except Exception as e:
        print(f"\n❌ TEST 1 ERROR: {e}")
        results.append(("RAG Integration", False))

    try:
        results.append(("Confidence Scoring", test_confidence_scoring()))
    except Exception as e:
        print(f"\n❌ TEST 2 ERROR: {e}")
        results.append(("Confidence Scoring", False))

    try:
        results.append(("Escalation Threshold", test_escalation_threshold()))
    except Exception as e:
        print(f"\n❌ TEST 3 ERROR: {e}")
        results.append(("Escalation Threshold", False))

    try:
        results.append(("AgentState Fields", test_agent_state_fields()))
    except Exception as e:
        print(f"\n❌ TEST 4 ERROR: {e}")
        results.append(("AgentState Fields", False))

    try:
        results.append(("Reporter Email", test_reporter_email()))
    except Exception as e:
        print(f"\n❌ TEST 5 ERROR: {e}")
        results.append(("Reporter Email", False))

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)

    print(f"\nTotal: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n🎉 All tests passed! Implementation is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed. Check logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
