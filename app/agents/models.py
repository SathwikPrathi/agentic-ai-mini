from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StepType(str, Enum):
    """Supported primitive operations.

    Keep this list small and well-defined; it becomes the contract between
    Planner (Agent A) and Worker (Agent B).
    """

    weather = "WEATHER"
    wiki_summary = "WIKIPEDIA_SUMMARY"
    calculate = "CALCULATE"
    time_in = "TIME_IN"
    summarize = "SUMMARIZE"


class PlanStep(BaseModel):
    id: str = Field(..., description="Unique step id used for referencing outputs")
    type: StepType
    input: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list, description="Step ids this step depends on")
    notes: Optional[str] = Field(default=None, description="Short rationale")


class Plan(BaseModel):
    """Structured plan produced by Agent A."""

    user_intent: str
    steps: List[PlanStep]
    output_style: str = Field(
        default="concise",
        description="How the final answer should read: concise, detailed, bullet, etc.",
    )


class ExecutedStep(BaseModel):
    step_id: str
    tool: str
    input: Dict[str, Any]
    output: Any


class ExecutionResult(BaseModel):
    """Results returned by Agent B."""

    steps: List[ExecutedStep]
    errors: List[str] = []
