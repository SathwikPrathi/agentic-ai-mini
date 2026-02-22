from __future__ import annotations

import ast
import operator as op
from typing import Any, Dict, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from app.core.exceptions import ToolExecutionError


class CalculatorInput(BaseModel):
    expression: str = Field(..., description="Math expression to evaluate (e.g., (2+3)/5)")


# Supported operators
_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.USub: op.neg,
    ast.Mod: op.mod,
}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    raise ToolExecutionError("Unsupported expression")


class CalculatorTool(BaseTool):
    name: str = "calculator"
    description: str = "Safely evaluate basic arithmetic expressions (+, -, *, /, %, **)."
    args_schema: Type[BaseModel] = CalculatorInput

    def _run(self, expression: str) -> Dict[str, Any]:
        try:
            tree = ast.parse(expression, mode="eval")
            value = _eval(tree.body)
            return {"expression": expression, "value": value}
        except Exception as e:  # noqa: BLE001
            raise ToolExecutionError(f"Calculator failed: {e}") from e
