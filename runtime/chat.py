"""Interactive local AI chat, with bounded, allowlisted tool calling.

Requires a running local Ollama API and an already downloaded model. No cloud
API keys, remote inference, shell execution, or destructive tools are used.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Any

from .tools import execute_tool

API_ROOT = "http://127.0.0.1:11434"
MAX_TURNS = 12
MAX_TOOL_ROUNDS = 3
MAX_INPUT_CHARS = 8000

TOOL_DEFS = [
    {"type": "function", "function": {"name": "calculate",
      "description": "Evaluate a basic arithmetic expression safely",
      "parameters": {"type": "object", "properties": {
          "expression": {"type": "string"}}, "required": ["expression"]}}},
    {"type": "function", "function": {"name": "utc_time",
      "description": "Obtain real current UTC time",
      "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "system_status",
      "description": "Read non-sensitive operating-system and resource summary",
      "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "process_summary",
      "description": "Read a short non-sensitive local process summary",
      "parameters": {"type": "object", "properties": {
          "limit": {"type": "integer", "minimum": 1, "maximum": 30}}}}},
    {"type": "function", "function": {"name": "network_summary",
      "description": "Summarize local network connection states without addresses",
      "parameters": {"type": "object", "properties": {}}}},
]


class OllamaClient:
    def __init__(self, model: str, timeout: int = 120):
        self.model = model
        self.timeout = timeout
        # No proxy for localhost, even on machines with proxy environment vars.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def chat(self, messages: list[dict[str, Any]], *, tools: bool = True) -> dict[str, Any]:
        request_body = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 800},
        }
        if tools:
            request_body["tools"] = TOOL_DEFS
        payload = json.dumps(request_body).encode("utf-8")
        req = urllib.request.Request(API_ROOT + "/api/chat", data=payload,
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
        with self.opener.open(req, timeout=self.timeout) as response:
            if response.status != 200:
                raise RuntimeError(f"Ollama HTTP status: {response.status}")
            data = json.loads(response.read(4_000_000).decode("utf-8"))
        message = data.get("message")
        if not isinstance(message, dict):
            raise ValueError("Ollama response missing message object")
        return message


class LocalAssistant:
    """Keeps bounded conversation context in RAM. No hidden persistence."""
    def __init__(self, client: OllamaClient):
        self.client = client
        self.history: list[dict[str, Any]] = []
        self.tool_history: list[dict[str, Any]] = []

    def reset(self) -> None:
        self.history.clear()
        self.tool_history.clear()

    def ask(self, question: str) -> str:
        if not isinstance(question, str) or not question.strip() or len(question) > MAX_INPUT_CHARS:
            raise ValueError("Input must contain 1 to 8,000 characters")
        system = {"role": "system", "content": (
            "You are Project Genesis, a local-first engineering assistant. "
            "You may use only the exposed read-only tools. Never claim an action "
            "succeeded if its tool result reports an error. Do not invent "
            "system state, time, model executions, or file edits. Explicitly "
            "state uncertainty. If asked to write files or run commands, "
            "provide a reviewable suggestion instead of claiming execution."
        )}
        user = {"role": "user", "content": question.strip()}
        context = [system] + self.history[-MAX_TURNS * 2:] + [user]
        tool_records: list[dict[str, Any]] = []
        try:
            for round_number in range(MAX_TOOL_ROUNDS + 1):
                response = self.client.chat(context, tools=round_number < MAX_TOOL_ROUNDS)
                calls = response.get("tool_calls") or []
                if not isinstance(calls, list):
                    raise ValueError("Invalid tool calls returned by model")
                if not calls:
                    answer = str(response.get("content") or "").strip()
                    if not answer:
                        raise ValueError("Model returned an empty answer")
                    self.history.extend([user, {"role": "assistant", "content": answer}])
                    self.history = self.history[-MAX_TURNS * 2:]
                    self.tool_history = tool_records
                    return answer
                if round_number >= MAX_TOOL_ROUNDS:
                    raise RuntimeError("Tool round limit exceeded")
                context.append({"role": "assistant", "content": str(response.get("content") or ""),
                                "tool_calls": calls})
                for call in calls[:5]:
                    function = call.get("function", {}) if isinstance(call, dict) else {}
                    name = function.get("name", "")
                    arguments = function.get("arguments", {})
                    if isinstance(arguments, str):
                        try:
                            arguments = json.loads(arguments)
                        except json.JSONDecodeError:
                            arguments = None
                    result = execute_tool(name, arguments)
                    tool_records.append(result)
                    context.append({"role": "tool", "tool_name": str(name),
                                    "content": json.dumps(result)})
                if len(calls) > 5:
                    context.append({"role": "tool", "tool_name": "genesis_policy",
                                    "content": json.dumps({"ok": False, "error": "Tool call batch exceeded 5"})})
            raise RuntimeError("Tool call budget exhausted")
        except Exception:
            # Failed turns are not committed to history.
            self.tool_history = tool_records
            raise
