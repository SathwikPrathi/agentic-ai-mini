class AgenticAIError(Exception):
    """Base exception for the app."""


class ToolExecutionError(AgenticAIError):
    """Raised when a tool call fails."""


class PlanningError(AgenticAIError):
    """Raised when we can't build a valid plan."""
