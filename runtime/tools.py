"""Allowlisted read-only tools. No shell, arbitrary Python, or state mutations."""
from __future__ import annotations

import ast
import operator
import platform
import sys
from datetime import datetime, timezone
from typing import Any, Callable

try:
    import psutil
except ImportError:  # dependency-free demonstration remains usable
    psutil = None

_MAX_EXPRESSION = 140
_BINOPS = {ast.Add: operator.add, ast.Sub: operator.sub,
           ast.Mult: operator.mul, ast.Div: operator.truediv}
_UNARYOPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _calculate_ast(node: ast.AST, depth: int = 0) -> float:
    if depth > 12:
        raise ValueError("Expression exceeds maximum depth")
    if isinstance(node, ast.Expression):
        return _calculate_ast(node.body, depth + 1)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        val = float(node.value)
        if not (-1e12 <= val <= 1e12):
            raise ValueError("Number outside permitted range")
        return val
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARYOPS:
        return _UNARYOPS[type(node.op)](_calculate_ast(node.operand, depth + 1))
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        left = _calculate_ast(node.left, depth + 1)
        right = _calculate_ast(node.right, depth + 1)
        out = _BINOPS[type(node.op)](left, right)
        if not (-1e12 <= out <= 1e12):
            raise ValueError("Result outside permitted range")
        return out
    raise ValueError("Unsupported arithmetic syntax")


def calculate(expression: str) -> dict[str, Any]:
    if not isinstance(expression, str) or len(expression) > _MAX_EXPRESSION:
        raise ValueError("Expression missing or too long")
    return {"expression": expression, "value": _calculate_ast(ast.parse(expression, mode="eval"))}


def utc_time() -> dict[str, str]:
    return {"utc": datetime.now(timezone.utc).isoformat()}


def system_status() -> dict[str, Any]:
    result: dict[str, Any] = {
        "platform": platform.system(),
        "python": sys.version.split()[0],
        "psutil_available": psutil is not None,
    }
    if psutil is not None:
        mem = psutil.virtual_memory()
        result.update({"logical_cpus": psutil.cpu_count(),
                       "memory_total_gib": round(mem.total / (1024 ** 3), 2),
                       "memory_used_percent": mem.percent})
    return result


def process_summary(limit: int = 8) -> dict[str, Any]:
    if psutil is None:
        raise RuntimeError("psutil is required for process inspection")
    if not isinstance(limit, int) or not (1 <= limit <= 30):
        raise ValueError("limit must be an integer between 1 and 30")
    entries = []
    for process in psutil.process_iter(attrs=["pid", "name"]):
        try:
            info = process.info
            entries.append({"pid": int(info["pid"]), "name": str(info.get("name") or "")[:80]})
            if len(entries) >= limit:
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return {"count_sampled": len(entries), "processes": entries}


def network_summary() -> dict[str, Any]:
    if psutil is None:
        raise RuntimeError("psutil is required for network inspection")
    connections = psutil.net_connections(kind="inet")
    by_state: dict[str, int] = {}
    for connection in connections:
        state = str(connection.status)
        by_state[state] = by_state.get(state, 0) + 1
    # No IP addresses, port mappings, or private payloads are exported.
    return {"connections_visible": len(connections), "by_state": by_state}


# All tools are defined here. No arbitrary code execution or external HTTP.
_TOOLS: dict[str, Callable[..., dict[str, Any]]] = {
    "calculate": calculate,
    "utc_time": utc_time,
    "system_status": system_status,
    "process_summary": process_summary,
    "network_summary": network_summary,
}


def tool_names() -> tuple[str, ...]:
    return tuple(sorted(_TOOLS))


def execute_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(name, str) or name not in _TOOLS:
        return {"ok": False, "tool": str(name)[:80], "error": "Tool not allowlisted"}
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict) or len(arguments) > 8:
        return {"ok": False, "tool": name, "error": "Invalid tool arguments"}
    try:
        value = _TOOLS[name](**arguments)
        return {"ok": True, "tool": name, "data": value}
    except (ValueError, TypeError, ZeroDivisionError, RuntimeError, OverflowError,
            PermissionError, OSError) as exc:
        return {"ok": False, "tool": name, "error": str(exc)[:300]}
    except Exception as exc:
        return {"ok": False, "tool": name, "error": "Unexpected tool failure: " + type(exc).__name__}
