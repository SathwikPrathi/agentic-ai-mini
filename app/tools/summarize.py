import json
from typing import Dict, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict


class SummarizeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")  # good hygiene; stable schema
    text: str = Field(..., description="Text (or JSON string) to summarize")
    max_chars: int = Field(default=400, ge=50, le=2000, description="Hard character limit")


class RuleBasedSummarizeTool(BaseTool):
    name: str = "summarize"
    description: str = (
        "Create a short summary from text (or JSON string) using simple rules. "
        "No LLM required."
    )
    args_schema: Type[BaseModel] = SummarizeInput

    def _run(self, text: str, max_chars: int = 400) -> Dict[str, str]:
        parsed = None
        s = (text or "").strip()

        # If it's JSON-ish, try parsing to format nicely before truncating
        if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
            try:
                parsed = json.loads(s)
            except Exception:
                parsed = None

        raw = json.dumps(parsed, ensure_ascii=False, indent=2) if isinstance(parsed, (dict, list)) else s
        raw = raw.strip()

        if len(raw) <= max_chars:
            return {"summary": raw}

        snippet = raw[:max_chars]
        # try to cut on a nice boundary
        for sep in [". ", "\n", "; "]:
            cut = snippet.rfind(sep)
            if cut > max_chars * 0.6:
                snippet = snippet[: cut + len(sep)].strip()
                break

        if not snippet.endswith("..."):
            snippet = snippet.rstrip() + "..."
        return {"summary": snippet}