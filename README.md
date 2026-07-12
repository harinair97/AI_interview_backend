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

## Stage 4: PostgreSQL persistence

Start the local PostgreSQL container and apply the schema migration:

```powershell
docker compose up -d postgres
.venv\Scripts\alembic.exe upgrade head
```

Interview creation now runs as one application transaction:

```text
run LangGraph -> encode typed state -> save interview snapshot
              -> append ordered events -> commit
```

If any database operation fails, the transaction rolls back. Retrieve a saved
interview, including its runtime state and event history, with:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/interviews/<interview-id>
```

Tests override the PostgreSQL session dependency with an in-memory SQLite
database. This keeps repository and API persistence tests isolated and fast;
the application itself uses `DATABASE_URL` from `.env`.

The Docker database is exposed on host port `55432` to avoid conflicts with a
locally installed PostgreSQL server that commonly uses port `5432`.

## Stage 5: answer turns and evaluation workflow

Submit a candidate answer to a persisted interview:

```powershell
$answer = @{ answer = "I would first measure the bottleneck, then compare caching and database optimization trade-offs." } | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri http://127.0.0.1:8000/api/v1/interviews/<interview-id>/answers `
    -ContentType "application/json" `
    -Body $answer
```

Each answer runs through a separate LangGraph:

```text
record answer -> evaluate -> recommend action -> validate policy
              -> update state -> render interviewer message
```

The transaction updates the current interview snapshot and appends four events
with payloads: the candidate answer, evaluation, approved decision, and next
interviewer message. Follow-up responses do not increment the number of planned
questions answered, and answers are rejected after completion.

The current evaluator uses answer length to exercise clarification, follow-up,
and move-on paths deterministically. Its scores are workflow scaffolding, not a
real assessment of technical correctness; structured LLM evaluation is the next
replacement point.

## Stage 6: OpenAI structured agents

Copy `.env.example` to `.env` and set your key locally:

```powershell
Copy-Item .env.example .env
```

```env
OPENAI_API_KEY=your-api-key
OPENAI_PLANNER_MODEL=gpt-5.4-mini
OPENAI_EVALUATION_MODEL=gpt-5.4-mini
OPENAI_ORCHESTRATOR_MODEL=gpt-5.4-mini
OPENAI_INTERVIEW_MODEL=gpt-5.4-mini
OPENAI_TIMEOUT_SECONDS=30
OPENAI_MAX_RETRIES=2
```

Never commit `.env`; it is excluded by `.gitignore`. Restart FastAPI after
changing environment variables because the agent clients are created when the
application modules load.

The Planner, Evaluation, Orchestrator, and Interview Agents use the OpenAI
Responses API and parse responses directly into `PlannerOutput`,
`EvaluationResult`, `OrchestratorDecision`, and `InterviewerOutput`. The
orchestrator receives compact decision context rather than the full plan,
candidate documents, or transcript. Every orchestrator result still passes
through the deterministic Python policy validator.

The Interview Agent phrases both the opening question and later messages. Its
candidate-safe context excludes evaluation scores, missing-concept lists,
orchestrator reasons, and confidence. It receives only the approved instruction,
current planned question, target role, section, and relevant candidate answer.

The Planner Agent runs once when an interview is created. It uses the role, job
description, candidate summary, requested competencies, difficulty, and question
count to design role-specific section names and assessment objectives. Python
attaches the original goal and rejects plans with the wrong question count,
unordered or duplicate sections, duplicate question IDs, undeclared
competencies, or missing requested competencies. Rejected or failed model plans
use the deterministic planner fallback.

If the key is absent, a request times out, the provider fails, or structured
output cannot be parsed, the affected agent logs the error type without the
candidate answer and uses its deterministic implementation. SDK retries and
timeouts are controlled by the environment settings above.

## Architectural rule

```text
AI recommends -> Python validates -> Python executes -> database persists
```
