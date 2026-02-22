from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., description="Natural language request from the user")
    use_llm: Optional[bool] = Field(
        default=None,
        description=(
            "Override LLM usage. If omitted, the server will use the LLM when an API key is configured. "
            "If no API key is configured, it will fall back to rule-based planning/execution."
        ),
    )


class StepResult(BaseModel):
    step_id: str
    tool: str
    input: Dict[str, Any]
    output: Any


class QueryResponse(BaseModel):
    trace_id: str
    final_answer: str
    plan: Dict[str, Any]
    steps: List[StepResult]
    warnings: List[str] = []
