import sys
from pathlib import Path

print("🔍 Validating SRE Agent Setup...\n")

errors = []
warnings = []

print("1. Checking directory structure...")
required_dirs = [
    "agent/nodes",
    "agent/prompts",
    "agent/schemas",
    "agent/utils",
    "apps/backend/app/services",
    "data/incidents"
]

for dir_path in required_dirs:
    full_path = Path(dir_path)
    if full_path.exists():
        print(f"   ✅ {dir_path}")
    else:
        print(f"   ❌ {dir_path}")
        errors.append(f"Missing directory: {dir_path}")

print("\n2. Checking required files...")
required_files = [
    "requirements.txt",
    ".env.example",
    "agent/__init__.py",
    "agent/config.py",
    "agent/state.py",
    "agent/graph.py",
    "agent/nodes/classify.py",
    "agent/nodes/extract.py",
    "agent/nodes/summarize.py",
    "agent/nodes/route.py",
    "agent/prompts/classify_prompt.txt",
    "agent/prompts/extract_prompt.txt",
    "agent/prompts/summarize_prompt.txt",
    "agent/prompts/route_prompt.txt",
    "agent/schemas/input_schema.py",
    "agent/schemas/output_schema.py",
    "agent/utils/logger.py",
    "agent/utils/llm_client.py",
    "agent/utils/prompts.py",
    "apps/backend/app/main.py",
    "apps/backend/app/services/agent_service.py"
]

for file_path in required_files:
    full_path = Path(file_path)
    if full_path.exists():
        print(f"   ✅ {file_path}")
    else:
        print(f"   ❌ {file_path}")
        errors.append(f"Missing file: {file_path}")

print("\n3. Checking environment configuration...")
env_file = Path(".env")
if env_file.exists():
    print("   ✅ .env file exists")
    
    with open(env_file, "r") as f:
        env_content = f.read()
        
    if "GEMINI_API_KEY" in env_content:
        if "your_gemini_api_key_here" in env_content or "your_api_key" in env_content:
            print("   ⚠️  GEMINI_API_KEY not configured (using placeholder)")
            warnings.append("Please set your actual GEMINI_API_KEY in .env")
        else:
            print("   ✅ GEMINI_API_KEY configured")
    else:
        print("   ❌ GEMINI_API_KEY not found in .env")
        errors.append("GEMINI_API_KEY not configured in .env")
else:
    print("   ⚠️  .env file not found")
    warnings.append("Create .env file from .env.example and configure GEMINI_API_KEY")

print("\n4. Checking Python dependencies...")
try:
    import langgraph
    print("   ✅ langgraph")
except ImportError:
    print("   ❌ langgraph")
    errors.append("langgraph not installed")

try:
    import langchain
    print("   ✅ langchain")
except ImportError:
    print("   ❌ langchain")
    errors.append("langchain not installed")

try:
    import google.genai
    print("   ✅ google-genai")
except ImportError:
    print("   ❌ google-genai")
    errors.append("google-genai not installed")

try:
    import pydantic
    print("   ✅ pydantic")
except ImportError:
    print("   ❌ pydantic")
    errors.append("pydantic not installed")

try:
    import fastapi
    print("   ✅ fastapi")
except ImportError:
    print("   ❌ fastapi")
    errors.append("fastapi not installed")

try:
    import structlog
    print("   ✅ structlog")
except ImportError:
    print("   ❌ structlog")
    errors.append("structlog not installed")

print("\n5. Testing agent imports...")
sys.path.insert(0, str(Path(__file__).parent))

try:
    from agent.schemas import IncidentReport, TriageResult
    print("   ✅ Schemas import successfully")
except Exception as e:
    print(f"   ❌ Schemas import failed: {e}")
    errors.append(f"Schema import error: {e}")

try:
    from agent.state import AgentState
    print("   ✅ State import successfully")
except Exception as e:
    print(f"   ❌ State import failed: {e}")
    errors.append(f"State import error: {e}")

try:
    from agent.nodes import classify, extract, summarize, route
    print("   ✅ Nodes import successfully")
except Exception as e:
    print(f"   ❌ Nodes import failed: {e}")
    errors.append(f"Nodes import error: {e}")

try:
    from agent.utils import get_logger, load_prompt
    print("   ✅ Utils import successfully")
except Exception as e:
    print(f"   ❌ Utils import failed: {e}")
    errors.append(f"Utils import error: {e}")

print("\n" + "="*80)
print("VALIDATION SUMMARY")
print("="*80)

if errors:
    print(f"\n❌ Found {len(errors)} error(s):")
    for error in errors:
        print(f"   • {error}")

if warnings:
    print(f"\n⚠️  Found {len(warnings)} warning(s):")
    for warning in warnings:
        print(f"   • {warning}")

if not errors and not warnings:
    print("\n✅ All checks passed! Setup is complete.")
    print("\nNext steps:")
    print("   1. Configure GEMINI_API_KEY in .env")
    print("   2. Run: python example_usage.py")
    print("   3. Run: python test_agent.py")
    print("   4. Run: python start_backend.py")
elif not errors:
    print("\n✅ Setup is mostly complete!")
    print("\nPlease address the warnings above, then:")
    print("   1. Run: python example_usage.py")
    print("   2. Run: python test_agent.py")
else:
    print("\n❌ Setup is incomplete. Please fix the errors above.")
    print("\nTo install dependencies:")
    print("   pip install -r requirements.txt")
    sys.exit(1)

print("\n" + "="*80)
