import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.chdir(Path(__file__).parent / "apps" / "backend")

import uvicorn

if __name__ == "__main__":
    print("🚀 Starting SRE Agent Backend API...")
    print("📍 API will be available at: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("=" * 80)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
