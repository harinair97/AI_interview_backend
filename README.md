# Hybrid AI Interview Orchestrator

A FastAPI backend that uses LangGraph to coordinate interview agents while a
deterministic Python policy layer owns state transitions and hard limits.

## Stage 1: run the foundation

Python 3.11 or newer is required.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000/docs` or request:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/interviews/demo
```

The demo endpoint invokes a credential-free LangGraph. It exists to verify the
workflow boundary before model providers, persistence, and the four production
agents are introduced.

## Architectural rule

```text
AI recommends -> Python validates -> Python executes -> database persists
```

