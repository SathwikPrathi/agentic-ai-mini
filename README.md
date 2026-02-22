# Agentic AI Mini-Project (FastAPI + CrewAI)

This project implements the assignment requirements with **two collaborating agents**:

- **Agent A (Planner):** converts a user’s natural-language request into a structured plan (small steps)
- **Agent B (Executor):** executes those steps using tools (APIs) and returns structured results
- Agent A then compiles the results into the final response

The service is exposed via a small **FastAPI** server.

## Key Features

- ✅ 2-agent workflow (Planner ↔ Executor)
- ✅ Tool-based execution (weather, Wikipedia summary, calculator, time zone)
- ✅ Clean separation of concerns (API / service / agents / tools)
- ✅ Basic production hygiene: retries, timeouts, caching, structured responses
- ✅ Works with an LLM (CrewAI) **or** falls back to deterministic planning/execution if no API key is configured

## Architecture (High-level)

1. `POST /query` receives a natural language request
2. **Agent A** produces a `Plan` (JSON)
3. **Agent B** executes the plan with tools and returns an `ExecutionResult` (JSON)
4. **Agent A** synthesizes a final answer for the user

In CrewAI mode, Agent A and Agent B communicate via **task context** (the plan becomes context for the executor; the execution becomes context for the final response).

## Tools Implemented

- **Weather (Open-Meteo)** – current conditions for a city (no API key required)
- **Wikipedia Summary** – quick topic summaries
- **Calculator** – safe arithmetic evaluation (AST-based)
- **Time in Timezone** – via worldtimeapi.org
- **Summarize (rule-based)** – simple summarization for fallback mode

## Running Locally

### 1) Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure environment variables

Copy the example env file:

```bash
cp .env.example .env
```

If you want CrewAI + LLM planning, set:

- `OPENAI_API_KEY=...`
- `MODEL=openai/gpt-4o-mini` (or another supported model)

> Note: CrewAI expects provider-prefixed model names (e.g., `openai/gpt-4o-mini`).

### 4) Start the API

```bash
uvicorn app.main:app --reload --port 8000
```

Open docs:

- http://127.0.0.1:8000/docs

## Example Usage

### Weather + summary

```bash
curl -X POST http://127.0.0.1:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"Get the current weather in New York and give me a short summary."}'
```

Example response (shape):

```json
{
  "trace_id": "...",
  "final_answer": "It is currently ... in New York...",
  "plan": {"user_intent": "...", "steps": [...]},
  "steps": [{"step_id":"step_1","tool":"weather","input":{...},"output":{...}}],
  "warnings": []
}
```

### Wikipedia summary

```bash
curl -X POST http://127.0.0.1:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"Tell me about FastAPI"}'
```

### Calculator

```bash
curl -X POST http://127.0.0.1:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"Calculate (2+3)*4"}'
```

## Project Structure

```text
app/
  main.py              # FastAPI entrypoint
  schemas.py           # API request/response models
  service.py           # Orchestration + mode selection (CrewAI vs fallback)
  agents/
    crew.py            # CrewAI two-agent pipeline
    prompts.py         # Planner / Executor / Final instructions
    models.py          # Pydantic schemas for plan + execution
    rule_based.py      # Deterministic planner fallback
    deterministic_runner.py  # Deterministic executor fallback
  tools/
    weather.py         # Open-Meteo tool
    wiki.py            # Wikipedia summary tool
    calculator.py      # Safe calculator tool
    time.py            # Timezone tool
    summarize.py       # Rule-based summarizer
    http.py            # httpx client + retries
tests/
```

## Notes / Best Practices

- **Timeouts + retries**: all external HTTP calls use `httpx` with retries
- **Caching**: geocoding and weather calls are cached (TTL)
- **Typed contracts**: Agent A and Agent B communicate via Pydantic models (`Plan`, `ExecutionResult`)
- **Safe execution**: calculator uses AST parsing (no `eval`)
