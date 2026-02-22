
# Agentic AI Mini-Project (Python) — Two-Agent System

This project implements a simple **multi-agent AI system** with **two agents** that collaborate to fulfill a user request end-to-end:

- **Agent A (Planner / Router):** Understands the user’s natural-language query, decides whether tools are needed, and produces a structured plan.
- **Agent B (Executor):** Executes the plan steps by calling the appropriate tools and returns results.
- **Final Response (Synthesizer):** Produces a clean final answer for the user based on tool outputs (or answers directly if tools aren’t required).

The system is served via a **FastAPI** endpoint (`POST /query`) and supports both **tool-based tasks** (e.g., weather/time/calculation) and **general questions** (direct LLM answers).

---

## Features

✅ Two-agent architecture (Planner + Executor)  
✅ Programmatic inter-agent communication (structured plan + execution results)  
✅ Tool routing (Agent decides whether to call tools or answer directly)  
✅ Error resilience (tool failures are handled; user gets a clean answer)  
✅ Modular Python code + clear API interface  
✅ Multiple sample inputs/outputs provided below

---

## Tech Stack

- Python 3.10+ (recommended 3.11)
- FastAPI + Uvicorn
- OpenAI (LLM for planning + direct answering + final synthesis)
- Tooling layer (weather / time / calculator / summarize)

---

## Project Structure (High Level)

```

app/
main.py                # FastAPI entrypoint
service.py             # Orchestration: plan -> execute -> finalize
agents/
planner.py           # Agent A: produces plan
executor.py          # Agent B: executes steps/tools
prompts.py           # Prompts/instructions for agents
deterministic_runner.py  # Optional deterministic execution
tools/
weather.py           # Weather tool (Open-Meteo)
time.py              # Time tool (timezone-based)
calculator.py        # Calculator tool
summarize.py         # Simple summary tool

````

---

## Setup & Installation

### 1) Clone the repo
```bash
git clone <YOUR_REPO_URL>
cd agentic-ai-mini
````

### 2) Create a virtual environment

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file (or export in your shell) with:

```bash
OPENAI_API_KEY="YOUR_KEY_HERE"
# Optional (if your code supports selecting model):
OPENAI_MODEL="openai/gpt-5.1-chat-latest"
```

> If `OPENAI_API_KEY` is missing, LLM-based planning/direct answers won’t work.

---

## Run the Server

```bash
uvicorn app.main:app --reload --port 8001
```

Open Swagger UI:

* [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)

---

## API Usage

### Endpoint

`POST /query`

### Example request body

```json
{
  "query": "Get the current weather in New York and summarize it."
}
```

### Example response body (shape)

```json
{
  "trace_id": "uuid-here",
  "final_answer": "Human-friendly response here...",
  "plan": {
    "user_intent": "...",
    "steps": [
      { "id": "step1", "type": "WEATHER", "input": { "location": "..." } }
    ],
    "output_style": "concise"
  },
  "steps": [
    {
      "step_id": "step1",
      "tool": "functions.weather",
      "input": { "...": "..." },
      "output": { "...": "..." }
    }
  ],
  "warnings": []
}
```

**Notes**

* `trace_id` helps debug/log a single run.
* `plan.steps` shows what Agent A planned.
* `steps[]` shows what Agent B executed.
* `final_answer` is what the user should read.
* Tool failures (if any) are handled gracefully; the user still receives a clean final response.

---

## How the Agents Work

### Agent A — Planner/Router

Given a user query, Agent A decides:

1. **DIRECT_ANSWER**: No tools needed → answer directly using LLM.
2. **TOOL_PLAN**: Tools needed → generate a plan with step types and inputs.
3. **CLARIFY**: Missing critical details → ask a single clarifying question.

### Agent B — Executor

Agent B reads the plan and executes each step using the appropriate tool:

* Weather → weather API/tool
* Time → timezone tool
* Calculator → math evaluation tool
* Summarize → summary tool

### Final Synthesizer

Combines tool outputs into a clean response. If a tool fails, the system can still produce a helpful answer.

---

## Examples (5)

Below are five example inputs and what you can expect as output.
(Exact values like temperature/time will vary because they depend on real-time APIs.)

---

### Example 1 — Weather + Summary (Tool Plan)

**Input**

```json
{ "query": "Get the current weather in New York and give me a short summary." }
```

**Expected Output (example)**

```json
{
  "trace_id": "....",
  "final_answer": "In New York right now, it’s around 6°C with moderate winds. Overall, it feels cool—consider a light jacket if you're heading out.",
  "plan": {
    "user_intent": "Get current weather and summarize",
    "steps": [
      { "id": "step1", "type": "WEATHER", "input": { "location": "New York" }, "depends_on": [] },
      { "id": "step2", "type": "SUMMARIZE", "input": { "from_step": "step1" }, "depends_on": ["step1"] }
    ],
    "output_style": "concise"
  },
  "steps": [
    {
      "step_id": "step1",
      "tool": "functions.weather",
      "input": { "location": "New York" },
      "output": { "temperature_c": 6.2, "wind_kph": 18.0, "weather_code": 3 }
    },
    {
      "step_id": "step2",
      "tool": "functions.summarize",
      "input": { "text": "..." },
      "output": "Short summary text..."
    }
  ],
  "warnings": []
}
```

---

### Example 2 — Time in a Timezone (Tool Plan)

**Input**

```json
{ "query": "What time is it in Asia/Kolkata right now?" }
```

**Expected Output (example)**

```json
{
  "trace_id": "....",
  "final_answer": "In Asia/Kolkata, it’s currently 2:15 PM (IST).",
  "plan": {
    "user_intent": "Get current time in Asia/Kolkata",
    "steps": [
      { "id": "step1", "type": "TIME_IN", "input": { "timezone": "Asia/Kolkata" }, "depends_on": [] }
    ],
    "output_style": "concise"
  },
  "steps": [
    {
      "step_id": "step1",
      "tool": "functions.time_in",
      "input": { "timezone": "Asia/Kolkata" },
      "output": { "datetime": "2026-02-22T14:15:12+05:30", "timezone": "Asia/Kolkata" }
    }
  ],
  "warnings": []
}
```

---

### Example 3 — Calculator (Tool Plan)

**Input**

```json
{ "query": "Calculate (12 * 5) + 99." }
```

**Expected Output (example)**

```json
{
  "trace_id": "....",
  "final_answer": "(12 * 5) + 99 = 159",
  "plan": {
    "user_intent": "Compute a math expression",
    "steps": [
      { "id": "step1", "type": "CALCULATOR", "input": { "expression": "(12 * 5) + 99" }, "depends_on": [] }
    ],
    "output_style": "concise"
  },
  "steps": [
    {
      "step_id": "step1",
      "tool": "functions.calculator",
      "input": { "expression": "(12 * 5) + 99" },
      "output": { "result": 159 }
    }
  ],
  "warnings": []
}
```

---

### Example 4 — General Knowledge Question (Direct Answer, No Tools)

**Input**

```json
{ "query": "Explain agentic AI in simple terms." }
```

**Expected Output (example)**

```json
{
  "trace_id": "....",
  "final_answer": "Agentic AI is when an AI system can plan and take steps to achieve a goal—like breaking a task into smaller actions, using tools when needed, and checking results—rather than only answering in one shot.",
  "plan": {
    "user_intent": "DIRECT_ANSWER",
    "steps": [],
    "output_style": "concise"
  },
  "steps": [],
  "warnings": []
}
```

---

### Example 5 — Missing Details (Clarification)

**Input**

```json
{ "query": "What's the weather like?" }
```

**Expected Output (example)**

```json
{
  "trace_id": "....",
  "final_answer": "Sure — which city should I check the weather for?",
  "plan": {
    "user_intent": "CLARIFY",
    "steps": [],
    "output_style": "concise"
  },
  "steps": [],
  "warnings": []
}
```