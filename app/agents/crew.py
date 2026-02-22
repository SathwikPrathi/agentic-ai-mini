from __future__ import annotations

import json
import re
import ast
from typing import Any, Dict, Optional

import os

from crewai import Agent, Crew, LLM, Process, Task

from app.agents.models import ExecutionResult, Plan
from app.agents.prompts import FINAL_SYSTEM, PLANNER_SYSTEM, WORKER_SYSTEM
from app.core.config import Settings
from app.core.exceptions import PlanningError
from app.core.logging import get_logger
from app.tools.calculator import CalculatorTool
from app.tools.summarize import RuleBasedSummarizeTool
from app.tools.time import WorldTimeTool
from app.tools.weather import OpenMeteoWeatherTool
from app.tools.wiki import WikipediaSummaryTool


logger = get_logger(__name__)


def _build_llm(settings: Settings) -> Optional[LLM]:
    # CrewAI can also read credentials from env vars, but we keep it explicit.
    if settings.openai_api_key:
        # CrewAI's OpenAI provider reads OPENAI_API_KEY from the environment.
        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
        # NOTE: model names should include provider prefix, e.g. "openai/gpt-4o-mini".
        # IMPORTANT: Some models/providers reject non-default temperature values.
        # If TEMPERATURE is unset, we omit it entirely and let the provider default.
        kwargs: Dict[str, Any] = {"model": settings.model}
        if settings.temperature is not None:
            kwargs["temperature"] = settings.temperature
        return LLM(**kwargs)
    return None


def build_crew(settings: Settings) -> Crew:
    """Build a 2-agent CrewAI pipeline.

    Agent A (Planner) creates a structured plan and composes the final answer.
    Agent B (Executor) executes plan steps using tools and returns raw results.
    """

    llm = _build_llm(settings)

    planner = Agent(
        role="Agent A: Planner",
        goal="Break down the user request into tool-executable steps and then compile a final response.",
        backstory="You are a senior solution architect who writes clear, minimal plans.",
        llm=llm,
        verbose=settings.crewai_verbose,
        allow_delegation=False,
        system_template=PLANNER_SYSTEM,
    )

    executor = Agent(
        role="Agent B: Executor",
        goal="Execute the plan accurately using available tools and return structured results.",
        backstory="You are a careful operator who never hallucinates tool outputs.",
        llm=llm,
        verbose=settings.crewai_verbose,
        allow_delegation=False,
        system_template=WORKER_SYSTEM,
        tools=[
            OpenMeteoWeatherTool(),
            WikipediaSummaryTool(),
            CalculatorTool(),
            WorldTimeTool(),
            RuleBasedSummarizeTool(),
        ],
    )

    # NOTE on structured outputs:
    # CrewAI supports `output_pydantic`, but in practice LLMs occasionally emit
    # almost-correct JSON (missing commas, trailing fences, etc.). CrewAI will
    # raise before we can recover. To make the service production-tolerant, we
    # request JSON-only outputs and validate/repair them ourselves post-run.
    plan_task = Task(
        description=(
            "User request: {user_request}\n\n"
            "Return ONLY valid JSON matching this Plan schema:\n{plan_schema}\n"
        ),
        expected_output="A valid JSON Plan.",
        agent=planner,
    )

    exec_task = Task(
        description=(
            "Execute the Plan from the previous task for the same user_request. "
            "Return ONLY valid JSON matching this ExecutionResult schema:\n{execution_schema}\n"
        ),
        expected_output="A valid JSON ExecutionResult.",
        agent=executor,
        context=[plan_task],
    )

    final_task = Task(
        description=(
            "Using the Plan and ExecutionResult from previous tasks, write the final answer to the user request: {user_request}\n\n"
            "Additional instructions:\n"
            f"{FINAL_SYSTEM}"
        ),
        expected_output="A helpful final answer.",
        agent=planner,
        context=[plan_task, exec_task],
        markdown=True,
    )

    return Crew(
        agents=[planner, executor],
        tasks=[plan_task, exec_task, final_task],
        process=Process.sequential,
    )


def kickoff(settings: Settings, user_request: str) -> Dict[str, Any]:
    """Run the Crew and return a dict with plan, execution, and final answer."""

    crew = build_crew(settings)
    inputs = {
        "user_request": user_request,
        "plan_schema": json.dumps(Plan.model_json_schema(), indent=2),
        "execution_schema": json.dumps(ExecutionResult.model_json_schema(), indent=2),
    }

    # CrewAI returns the output of the last task (final answer), but intermediate
    # task outputs are accessible through crew.tasks.
    final_answer = crew.kickoff(inputs=inputs)

    plan_out = crew.tasks[0].output
    exec_out = crew.tasks[1].output

    # Normalize to dicts for API responses
    plan = _normalize_task_output(plan_out, Plan)
    execution = _normalize_task_output(exec_out, ExecutionResult)

    return {
        "final_answer": str(final_answer),
        "plan": plan,
        "execution": execution,
    }


def _normalize_task_output(task_output: Any, model_type: Any) -> Dict[str, Any]:
    if task_output is None:
        raise PlanningError("Missing task output")

    # CrewAI output objects have a .raw field in many versions.
    raw = getattr(task_output, "raw", None)
    if raw is None:
        raw = task_output

    if isinstance(raw, model_type):
        return raw.model_dump()
    if isinstance(raw, dict):
        return model_type.model_validate(raw).model_dump()
    if isinstance(raw, str):
        data = _safe_parse_json_object(raw)
        return model_type.model_validate(data).model_dump()

    raise PlanningError(f"Unsupported task output type: {type(raw)}")


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
def _escape_newlines_in_json_strings(s: str) -> str:
    """
    OpenAI/CrewAI outputs sometimes include literal newlines inside quoted JSON strings.
    JSON forbids raw newlines inside strings, so we escape them to \\n.
    """
    out = []
    in_str = False
    esc = False

    for ch in s:
        if in_str:
            if esc:
                out.append(ch)
                esc = False
                continue
            if ch == "\\":
                out.append(ch)
                esc = True
                continue
            if ch == '"':
                out.append(ch)
                in_str = False
                continue
            # ✅ critical: escape raw newlines inside strings
            if ch == "\n":
                out.append("\\n")
                continue
            if ch == "\r":
                out.append("\\r")
                continue
            if ch == "\t":
                out.append("\\t")
                continue
            out.append(ch)
        else:
            if ch == '"':
                out.append(ch)
                in_str = True
            else:
                out.append(ch)

    return "".join(out)

def _safe_parse_json_object(text: str) -> Dict[str, Any]:
    """Best-effort JSON object parsing.

    CrewAI LLM runs can occasionally produce near-JSON. We:
    - remove markdown fences
    - extract the outermost {...}
    - remove trailing commas
    - fall back to Python-literal parsing for single quotes
    """

    txt = text.strip()
    txt = _FENCE_RE.sub("", txt).strip()

    # Extract likely JSON object payload if there's surrounding commentary.
    start = txt.find("{")
    end = txt.rfind("}")
    if start >= 0 and end > start:
        txt = txt[start : end + 1]

    # Remove trailing commas before ] or }
    txt = re.sub(r",\s*([\]}])", r"\1", txt)
    txt = _escape_newlines_in_json_strings(txt)

    try:
        data = json.loads(txt)
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object")
        return data
    except Exception:
        # Fall back: sometimes models emit python-ish dicts with single quotes.
        try:
            data = ast.literal_eval(txt)
            if not isinstance(data, dict):
                raise ValueError("Expected an object")
            return data
        except Exception as e:
            raise PlanningError(f"Could not parse JSON output (first 240 chars): {text.strip()[:240]}") from e
