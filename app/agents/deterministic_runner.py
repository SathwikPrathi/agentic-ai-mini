from __future__ import annotations

import json
import inspect
from typing import Any, Dict, List, Mapping

from app.agents.models import ExecutionResult, ExecutedStep, Plan, StepType
from app.core.exceptions import ToolExecutionError
from app.core.logging import get_logger
from app.tools.calculator import CalculatorTool
from app.tools.summarize import RuleBasedSummarizeTool
from app.tools.time import WorldTimeTool
from app.tools.weather import OpenMeteoWeatherTool
from app.tools.wiki import WikipediaSummaryTool


logger = get_logger(__name__)


def _deep_replace_placeholders(obj: Any, outputs: Mapping[str, Any]) -> Any:
    """Replace strings like '{{step_1.output}}' with actual JSON outputs."""

    if isinstance(obj, str):
        if obj.startswith("{{") and obj.endswith("}}"):
            key = obj[2:-2].strip()
            # expected 'step_X.output'
            step_id = key.split(".", 1)[0]
            return outputs.get(step_id)
        return obj
    if isinstance(obj, list):
        return [_deep_replace_placeholders(x, outputs) for x in obj]
    if isinstance(obj, dict):
        return {k: _deep_replace_placeholders(v, outputs) for k, v in obj.items()}
    return obj


async def run_plan(plan: Plan) -> ExecutionResult:
    """Execute a Plan without using an LLM.

    This is used as a fallback when LLM credentials are not configured.
    """

    tools = {
        StepType.weather: OpenMeteoWeatherTool(),
        StepType.wiki_summary: WikipediaSummaryTool(),
        StepType.calculate: CalculatorTool(),
        StepType.time_in: WorldTimeTool(),
        StepType.summarize: RuleBasedSummarizeTool(),
    }

    outputs: Dict[str, Any] = {}
    executed: List[ExecutedStep] = []
    errors: List[str] = []

    for step in plan.steps:
        tool = tools.get(step.type)
        if not tool:
            errors.append(f"Unsupported step type: {step.type}")
            continue

        step_input = _deep_replace_placeholders(step.input, outputs)
        try:
            # Prefer async if tool supports it.
            arun = getattr(tool, "_arun", None)
            if arun is not None and inspect.iscoroutinefunction(arun):
                out = await arun(**step_input)  # type: ignore[misc]
            else:
                # Many tools in this repo intentionally implement a *sync* _arun
                # (see SyncBaseTool). Never await a non-coroutine.
                out = tool._run(**step_input)
            outputs[step.id] = out
            executed.append(ExecutedStep(step_id=step.id, tool=tool.name, input=step_input, output=out))
        except ToolExecutionError as e:
            msg = f"Step {step.id} ({step.type}) failed: {e}"
            logger.exception(msg)
            errors.append(msg)
        except Exception as e:  # noqa: BLE001
            msg = f"Step {step.id} ({step.type}) crashed: {e}"
            logger.exception(msg)
            errors.append(msg)

    return ExecutionResult(steps=executed, errors=errors)
