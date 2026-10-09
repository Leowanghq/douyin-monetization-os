"""
Safe calculator — evaluates math expressions using only built-in Python ops.
No eval() — uses AST-based safe evaluation.
"""

import ast
import math
import operator

from agent.tools import BaseTool

# Allowed operators and functions
_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Mod: operator.mod,
}

_SAFE_FUNCS = {
    "abs": abs,
    "round": round,
    "max": max,
    "min": min,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "pi": math.pi,
    "e": math.e,
}


def _safe_eval(node):
    """Recursively evaluate a safe AST node."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    elif isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPS:
            raise ValueError(f"Unsafe operator: {op_type.__name__}")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return _SAFE_OPS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPS:
            raise ValueError(f"Unsafe unary operator: {op_type.__name__}")
        return _SAFE_OPS[op_type](_safe_eval(node.operand))
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function calls are allowed")
        name = node.func.id
        if name not in _SAFE_FUNCS:
            raise ValueError(f"Unsafe function: {name}")
        args = [_safe_eval(a) for a in node.args]
        return _SAFE_FUNCS[name](*args)
    elif isinstance(node, ast.Name):
        if node.id not in _SAFE_FUNCS:
            raise ValueError(f"Unknown name: {node.id}")
        return _SAFE_FUNCS[node.id]
    else:
        raise ValueError(f"Unsupported expression type: {type(node).__name__}")


class CalculatorTool(BaseTool):
    name = "calculator"
    description = "Safely evaluate a mathematical expression. Supports +, -, *, /, **, %, sqrt, sin, cos, log, pi, e, etc."
    parameters = {
        "expression": {
            "type": "string",
            "description": "The math expression to evaluate, e.g. '2 + 3 * 4' or 'sqrt(144)'.",
        },
    }

    def execute(self, expression: str) -> str:
        try:
            tree = ast.parse(expression.strip(), mode="eval")
            result = _safe_eval(tree)
            return f"{expression} = {result}"
        except Exception as e:
            return f"Calculation error: {e}"
