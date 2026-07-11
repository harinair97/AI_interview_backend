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

## Stage 2: deterministic safety policy

Every orchestrator recommendation now passes through a pure Python validator.
The validator enforces:

- maximum follow-up and clarification counts;
- required questions before changing sections;
- minimum coverage before ending the interview;
- an allow-list of available topics;
- a minimum orchestrator confidence;
- at least two consistent signals before changing difficulty.

When a recommendation is unsafe or uncertain, `fallback_policy.py` chooses the
next safe action from evaluator guidance and the remaining interview plan. These
rules do not call an LLM and can be tested deterministically.

## Stage 3: configurable interview planning

Create an interview with a role, difficulty, question count, and optional
competency list:

```powershell
$body = @{
    target_role = "Data Engineer"
    difficulty = "HARD"
    planned_question_count = 6
    competencies = @("SQL", "data modeling", "distributed systems")
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri http://127.0.0.1:8000/api/v1/interviews `
    -ContentType "application/json" `
    -Body $body
```

The Planner Agent produces ordered sections and question objectives. It does not
write candidate-facing dialogue. The graph derives its available topics,
coverage records, section order, and counters from this validated plan. The MVP
planner is deterministic; job descriptions and candidate summaries are already
accepted by the API contract and will be used by the later LLM-backed planner.

## Architectural rule

```text
AI recommends -> Python validates -> Python executes -> database persists
```
