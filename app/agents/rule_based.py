from __future__ import annotations

import re
from typing import List, Tuple

from app.agents.models import Plan, PlanStep, StepType


_LOCATION_RE = re.compile(r"\b(?:in|for)\s+(?P<loc>[A-Za-z][A-Za-z\s,.-]{2,})", re.IGNORECASE)


def build_plan(query: str) -> Plan:
    """Very small deterministic planner used when no LLM is configured.

    It is intentionally conservative: it only recognizes a few common intents and
    defaults to asking a clarifying question via a SUMMARIZE step.
    """

    q = query.strip()
    q_lower = q.lower()
    steps: List[PlanStep] = []

    # Weather
    if "weather" in q_lower or "temperature" in q_lower:
        loc_match = _LOCATION_RE.search(q)
        location = (loc_match.group("loc").strip() if loc_match else "")
        steps.append(
            PlanStep(id="step_1", type=StepType.weather, input={"location": location or "New York"})
        )
        if "summary" in q_lower or "summar" in q_lower:
            steps.append(
                PlanStep(
                    id="step_2",
                    type=StepType.summarize,
                    input={"text": "{{step_1.output}}"},
                    depends_on=["step_1"],
                )
            )
        return Plan(user_intent="Get weather and optionally summarize", steps=steps, output_style="concise")

    # Time in timezone
    if "time" in q_lower and "in " in q_lower:
        tz = q.split("in", 1)[-1].strip()
        steps.append(PlanStep(id="step_1", type=StepType.time_in, input={"timezone": tz or "Asia/Kolkata"}))
        return Plan(user_intent="Get current time", steps=steps, output_style="concise")

    # Calculation
    if q_lower.startswith("calculate") or any(ch.isdigit() for ch in q) and any(op in q for op in ["+", "-", "*", "/", "^"]):
        expr = q.replace("calculate", "").strip()
        steps.append(PlanStep(id="step_1", type=StepType.calculate, input={"expression": expr or q}))
        return Plan(user_intent="Evaluate arithmetic", steps=steps, output_style="concise")

    # Wikipedia-like lookup
    if q_lower.startswith("who is") or q_lower.startswith("what is") or "tell me about" in q_lower:
        topic = q
        for prefix in ["who is", "what is", "tell me about"]:
            if topic.lower().startswith(prefix):
                topic = topic[len(prefix) :].strip(" ?")
        steps.append(PlanStep(id="step_1", type=StepType.wiki_summary, input={"query": topic}))
        return Plan(user_intent="Look up a topic", steps=steps, output_style="concise")

    # Fallback: ask for clarification.
    steps.append(
        PlanStep(
            id="step_1",
            type=StepType.summarize,
            input={
                "text": (
                    "I can help with weather, Wikipedia summaries, calculations, and time zones. "
                    "Can you rephrase your request or specify what you'd like?"
                )
            },
        )
    )
    return Plan(user_intent="Clarification needed", steps=steps, output_style="concise")
