from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from app.agents.crew import kickoff as crew_kickoff
from app.agents.deterministic_runner import run_plan
from app.agents.models import ExecutionResult, Plan
from app.agents.rule_based import build_plan
from app.core.config import Settings
from app.core.logging import get_logger


logger = get_logger(__name__)


class AgenticAIService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def handle_query(self, query: str, use_llm: Optional[bool] = None) -> Dict[str, Any]:
        """Run an end-to-end request.

        If OPENAI_API_KEY is configured and use_llm isn't forcing False, uses CrewAI
        to plan + execute + synthesize. Otherwise, falls back to deterministic planning
        and tool execution.
        """

        trace_id = str(uuid.uuid4())
        warnings: List[str] = []

        llm_available = bool(self.settings.openai_api_key)
        use_llm_effective = llm_available if use_llm is None else use_llm

        if use_llm_effective:
            logger.info("trace=%s mode=crewai kickoff", trace_id)
            result = crew_kickoff(self.settings, query)
            plan = result["plan"]
            execution = result["execution"]
            final_answer = result["final_answer"]
        else:
            if use_llm is True and not llm_available:
                warnings.append("LLM requested, but OPENAI_API_KEY is not set. Falling back to rule-based mode.")
            logger.info("trace=%s mode=deterministic", trace_id)
            plan_model: Plan = build_plan(query)
            exec_model: ExecutionResult = await run_plan(plan_model)

            plan = plan_model.model_dump()
            execution = exec_model.model_dump()
            final_answer = self._compose_final_answer(plan_model, exec_model)

        # Transform execution.steps into API-friendly format
        steps = execution.get("steps", [])
        if isinstance(steps, list):
            api_steps = [
                {
                    "step_id": s.get("step_id"),
                    "tool": s.get("tool"),
                    "input": s.get("input"),
                    "output": s.get("output"),
                }
                for s in steps
            ]
        else:
            api_steps = []

        # Surface tool failures
        errors = execution.get("errors") or []
        warnings.extend(errors)

        return {
            "trace_id": trace_id,
            "final_answer": final_answer,
            "plan": plan,
            "steps": api_steps,
            "warnings": warnings,
        }

    def _compose_final_answer(self, plan: Plan, execution: ExecutionResult) -> str:
        """Small deterministic final answer composer."""

        if execution.errors:
            return "I ran into issues while executing your request: " + "; ".join(execution.errors)

        if not execution.steps:
            return "I couldn't execute any steps for that request."

        # Prefer explicit SUMMARIZE step output if present.
        for s in execution.steps[::-1]:
            if s.tool == "summarize" and isinstance(s.output, dict) and "summary" in s.output:
                return str(s.output["summary"])

        # Else, stringify the last tool output.
        last = execution.steps[-1]
        return f"{last.tool} result: {last.output}"
