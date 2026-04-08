import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agent.schemas.input_schema import IncidentReport
from agent.graph import run_triage_agent
import json


def test_catalog_issue():
    print("\n" + "="*80)
    print("TEST: Catalog Issue")
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


def save_test_result(result):
    output = {
        "test_name": "catalog_issue",
        "result": result.model_dump()
    }
    
    with open("test_catalog_result.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    
    print("\n" + "="*80)
    print("📁 Test result saved to test_catalog_result.json")
    print("="*80)


if __name__ == "__main__":
    print("\n🚀 Starting Catalog Issue Test...")
    print("="*80)
    
    try:
        result = test_catalog_issue()
        save_test_result(result)
        
        print("\n" + "="*80)
        print("🎉 TEST COMPLETED!")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
