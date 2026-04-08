import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agent import run_triage_agent, IncidentReport


def main():
    print("🚀 SRE Agent - Example Usage\n")
    
    print("Creating incident report...")
    report = IncidentReport(
        description="Users are getting timeout errors when trying to checkout. Payment page shows 500 error after clicking 'Pay Now' button.",
        source="QA"
    )
    
    print(f"Description: {report.description}")
    print(f"Source: {report.source}\n")
    
    print("Running triage agent...\n")
    result = run_triage_agent(report)
    
    print("="*80)
    print("TRIAGE RESULT")
    print("="*80)
    print(f"\n📋 Incident ID: {result.incident_id}")
    print(f"🏷️  Type: {result.incident_type}")
    print(f"🚨 Severity: {result.severity}")
    print(f"📦 Affected Plugin: {result.affected_plugin}")
    print(f"🔧 Layer: {result.layer}")
    print(f"👥 Assigned Team: {result.assigned_team}")
    
    print(f"\n📝 Technical Summary:")
    print(f"   {result.summary}")
    
    print(f"\n🔧 Suggested Actions:")
    for i, action in enumerate(result.suggested_actions, 1):
        print(f"   {i}. {action}")
    
    print(f"\n⏱️  Processing Time: {result.processing_time_ms}ms")
    print(f"🎯 Confidence Score: {result.confidence_score}")
    
    print("\n" + "="*80)
    print("✅ Triage completed successfully!")
    print("="*80)


if __name__ == "__main__":
    main()
