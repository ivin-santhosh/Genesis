"""Bounded, checkpointed plan -> tool execution -> deterministic verification.

This execution engine does not claim LLM reasoning or production SLAs.
It is a reproducible integration baseline; local model mode can be added only
after model outputs are schema-validated and its operational tests pass.
"""
from __future__ import annotations
import json
import uuid
from typing import Any

from .state import CheckpointStore
from .tools import execute_tool, tool_names

MAX_STEPS = 12
MAX_OUTPUT_CHARS = 60000

class WorkflowEngine:
    def __init__(self, store: CheckpointStore):
        self.store = store

    def plan(self, operations: list[dict[str, Any]], task_id: str | None = None) -> dict[str, Any]:
        if not isinstance(operations, list) or not (1 <= len(operations) <= MAX_STEPS):
            raise ValueError("Expected 1-12 operations")
        checked = []
        for i, step in enumerate(operations):
            if not isinstance(step, dict) or set(step) - {"tool", "args"}:
                raise ValueError(f"Invalid operation {i}")
            if step.get("tool") not in tool_names():
                raise ValueError(f"Tool not permitted at step {i}")
            args = step.get("args", {})
            if not isinstance(args, dict):
                raise ValueError("Tool args must be a mapping")
            # Ensure inputs can be safely serialized before they are persisted.
            if len(json.dumps(args, allow_nan=False)) > 8000:
                raise ValueError("Arguments too large")
            checked.append({"tool": step["tool"], "args": args})
        state = {
            "task_id": task_id or str(uuid.uuid4()),
            "status": "planned", "step_index": 0, "steps": checked,
            "results": [], "error": None, "verdict": None,
        }
        if self.store.load(state["task_id"]):
            raise ValueError("Task ID already exists")
        self.store.save(state["task_id"], state)
        return state

    def execute(self, task_id: str, max_new_steps: int | None = None) -> dict[str, Any]:
        state = self.store.load(task_id)
        if state is None:
            raise ValueError("Unknown task ID")
        if state["status"] in ("completed", "failed", "cancelled"):
            return state
        if max_new_steps is not None and (not isinstance(max_new_steps, int)
                                           or not 1 <= max_new_steps <= MAX_STEPS):
            raise ValueError("Invalid execution budget")
        allowed = max_new_steps if max_new_steps is not None else MAX_STEPS
        while state["step_index"] < len(state["steps"]) and allowed:
            idx = state["step_index"]
            step = state["steps"][idx]
            # Persist intent before tool dispatch. All tools in this runtime are
            # read-only; a future mutating tool needs idempotency and recovery.
            state["status"] = "running"
            state["inflight"] = idx
            self.store.save(task_id, state)
            result = execute_tool(step["tool"], step["args"])
            if len(json.dumps(result, default=str)) > MAX_OUTPUT_CHARS:
                result = {"ok": False, "tool": step["tool"], "error": "Tool output too large"}
            state["results"].append(result)
            state["step_index"] = idx + 1
            state.pop("inflight", None)
            allowed -= 1
            if not result["ok"]:
                state["status"] = "failed"
                state["error"] = f"step {idx}: {result['error']}"
                state["verdict"] = "FAIL"
                self.store.save(task_id, state)
                return state
            self.store.save(task_id, state)
        if state["step_index"] == len(state["steps"]):
            state["status"] = "completed"
            state["verdict"] = "PASS" if all(result["ok"] for result in state["results"]) else "FAIL"
        else:
            state["status"] = "paused"
        self.store.save(task_id, state)
        return state

    def resume(self, task_id: str) -> dict[str, Any]:
        state = self.store.load(task_id)
        if not state:
            raise ValueError("Unknown task ID")
        if "inflight" in state:
            # Checkpoint recovery must not silently replay potentially
            # non-idempotent operations after a crash.
            state["status"] = "failed"
            state["error"] = "Interrupted execution needs manual inspection"
            state["verdict"] = "FAIL"
            self.store.save(task_id, state)
            return state
        return self.execute(task_id)

    def cancel(self, task_id: str) -> dict[str, Any]:
        state = self.store.load(task_id)
        if not state:
            raise ValueError("Unknown task ID")
        if state["status"] not in ("completed", "failed"):
            state["status"] = "cancelled"
            state["verdict"] = "CANCELLED"
            self.store.save(task_id, state)
        return state
