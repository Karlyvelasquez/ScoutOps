# ScoutOps - SRE Incident Triage Agent

AgentX Hackathon 2026 - SRE Agent for automated incident triage and management.

## 🎯 Overview

ScoutOps is an intelligent SRE agent that automates the complete incident management process for e-commerce platforms. It transforms unstructured incident reports into architecture-aware, actionable engineering tasks in under 60 seconds.

## ✨ Features

- **Intelligent Classification**: Automatically categorizes incidents (checkout failures, login errors, catalog issues, etc.)
- **Entity Extraction**: Identifies affected services, features, and error patterns
- **Technical Summarization**: Generates actionable technical summaries for engineers
- **Smart Routing**: Assigns severity levels and routes to appropriate teams
- **Structured Output**: Returns validated JSON with complete triage information

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Google Gemini API Key ([Get one here](https://aistudio.google.com/app/apikey))

### Installation

1. Clone the repository
2. Create and activate virtual environment:
```bash
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Windows (CMD)
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

5. Run example:
```bash
python example_usage.py
```

6. Run tests:
```bash
python test_agent.py
```

## 📚 Documentation

- **[AGENT_SETUP.md](AGENT_SETUP.md)**: Complete setup and usage guide
- **[SRE_Agent_Team_Briefing.md](SRE_Agent_Team_Briefing.md)**: Technical briefing and architecture

## 🏗️ Architecture

```
Input → Classify → Extract → Summarize → Route → Output
```

The agent uses LangGraph to orchestrate a 4-node pipeline:
1. **Classify**: Determine incident type
2. **Extract**: Extract technical entities
3. **Summarize**: Generate technical summary
4. **Route**: Assign severity and team

## 🔧 API Usage

Start the backend:
```bash
cd apps/backend
uvicorn app.main:app --reload --port 8000
```

Create an incident:
```bash
curl -X POST http://localhost:8000/incident \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Users getting 500 error when trying to pay",
    "source": "QA"
  }'
```

## 📦 Project Structure

```
ScoutOps/
├── agent/                  # Agent pipeline
│   ├── nodes/             # Pipeline nodes
│   ├── prompts/           # LLM prompts
│   ├── schemas/           # Pydantic schemas
│   └── utils/             # Utilities
├── apps/
│   └── backend/           # FastAPI backend
├── data/
│   └── incidents/         # Stored results
└── test_agent.py          # Test suite
```

## 🎯 Supported Incident Types

- `checkout_failure`: Payment/order issues
- `login_error`: Authentication problems
- `catalog_issue`: Product display issues
- `cart_issue`: Shopping cart problems
- `inventory_issue`: Stock availability
- `shipping_issue`: Delivery problems
- `performance_issue`: Latency/timeouts

## 🛠️ Tech Stack

- **LangGraph**: Agent orchestration
- **Google Gemini 1.5 Flash**: LLM for analysis
- **FastAPI**: Backend API
- **Pydantic**: Data validation
- **Structlog**: Structured logging

## 📊 Performance

Typical processing time: **5-8 seconds** per incident

## 🔮 Roadmap

- [ ] RAG integration with Reaction Commerce codebase
- [ ] Multimodal analysis (images, logs)
- [ ] GitHub Issues integration
- [ ] Slack notifications
- [ ] Langfuse observability

## 📝 License

MIT License - see [LICENSE](LICENSE)

## 🏆 AgentX Hackathon 2026

Built for the AgentX Hackathon 2026 - Deadline: April 9, 2026 @ 9:00 PM COT
