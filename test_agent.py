import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agent.schemas.input_schema import IncidentReport
from agent.graph import run_triage_agent
import json


def test_checkout_failure():
    print("\n" + "="*80)
    print("TEST 1: Checkout Failure")
    print("="*80)
    
    report = IncidentReport(
        description="Users getting 500 error when trying to pay with credit card. Stripe timeout errors in logs.",
        source="QA"
    )
    
    result = run_triage_agent(report)
    
    print(f"\n✅ Incident Type: {result.incident_type}")
    print(f"✅ Severity: {result.severity}")
    print(f"✅ Affected Plugin: {result.affected_plugin}")
    print(f"✅ Assigned Team: {result.assigned_team}")
    print(f"✅ Layer: {result.layer}")
    print(f"\n📝 Summary:\n{result.summary}")
    print(f"\n🔧 Suggested Actions:")
    for i, action in enumerate(result.suggested_actions, 1):
        print(f"   {i}. {action}")
    print(f"\n⏱️  Processing Time: {result.processing_time_ms}ms")
    print(f"🎯 Confidence: {result.confidence_score}")
    
    assert result.incident_type == "checkout_failure"
    assert result.severity in ["P1", "P2"]
    assert "payment" in result.affected_plugin.lower()
    
    print("\n✅ TEST PASSED")
    return result


def test_login_error():
    print("\n" + "="*80)
    print("TEST 2: Login Error")
    print("="*80)
    
    report = IncidentReport(
        description="Users cannot log in to their accounts. Getting 'Invalid credentials' even with correct password.",
        source="soporte"
    )
    
    result = run_triage_agent(report)
    
    print(f"\n✅ Incident Type: {result.incident_type}")
    print(f"✅ Severity: {result.severity}")
    print(f"✅ Affected Plugin: {result.affected_plugin}")
    print(f"✅ Assigned Team: {result.assigned_team}")
    print(f"\n📝 Summary:\n{result.summary}")
    print(f"\n🔧 Suggested Actions:")
    for i, action in enumerate(result.suggested_actions, 1):
        print(f"   {i}. {action}")
    print(f"\n⏱️  Processing Time: {result.processing_time_ms}ms")
    
    assert result.incident_type == "login_error"
    
    print("\n✅ TEST PASSED")
    return result


def test_catalog_issue():
    print("\n" + "="*80)
    print("TEST 3: Catalog Issue")
    print("="*80)
    
    report = IncidentReport(
        description="Product images not loading on the catalog page. Search returns empty results.",
        source="monitoring"
    )
    
    result = run_triage_agent(report)
    
    print(f"\n✅ Incident Type: {result.incident_type}")
    print(f"✅ Severity: {result.severity}")
    print(f"✅ Affected Plugin: {result.affected_plugin}")
    print(f"✅ Assigned Team: {result.assigned_team}")
    print(f"\n📝 Summary:\n{result.summary}")
    print(f"\n🔧 Suggested Actions:")
    for i, action in enumerate(result.suggested_actions, 1):
        print(f"   {i}. {action}")
    print(f"\n⏱️  Processing Time: {result.processing_time_ms}ms")
    
    assert result.incident_type == "catalog_issue"
    
    print("\n✅ TEST PASSED")
    return result


def save_test_results(results):
    output = {
        "test_results": [
            {
                "test_name": "checkout_failure",
                "result": results[0].model_dump()
            },
            {
                "test_name": "login_error",
                "result": results[1].model_dump()
            },
            {
                "test_name": "catalog_issue",
                "result": results[2].model_dump()
            }
        ]
    }
    
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    
    print("\n" + "="*80)
    print("📁 Test results saved to test_results.json")
    print("="*80)


if __name__ == "__main__":
    print("\n🚀 Starting SRE Agent Tests...")
    print("="*80)
    
    try:
        results = []
        
        result1 = test_checkout_failure()
        results.append(result1)
        
        result2 = test_login_error()
        results.append(result2)
        
        result3 = test_catalog_issue()
        results.append(result3)
        
        save_test_results(results)
        
        print("\n" + "="*80)
        print("🎉 ALL TESTS PASSED!")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
