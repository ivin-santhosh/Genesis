"""Live stdio MCP boundary checks against the real server entrypoint."""
from __future__ import annotations

import importlib.util
import json
import queue
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP_SOURCE = ROOT / "tools" / "mcp_tools.py"
ALLOWED = {
    "add_float", "subtract_float", "multiply_float", "divide_float",
    "add_int", "subtract_int", "multiply_int", "divide_int",
    "get_datetime", "severity_score", "mitre_guess",
}


def _server_bootstrap() -> str:
    source = str(MCP_SOURCE)
    return f"""
import runpy
import sys
import types

def add_stub(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module

class _DDGS:
    def text(self, *args, **kwargs):
        return []

class _Stub:
    def __init__(self, *args, **kwargs):
        pass

class _CacheMode:
    BYPASS = "BYPASS"

add_stub("duckduckgo_search", DDGS=_DDGS)
add_stub("crawl4ai", AsyncWebCrawler=_Stub, CrawlerRunConfig=_Stub, CacheMode=_CacheMode)
add_stub("matplotlib", use=lambda *args, **kwargs: None)
add_stub("matplotlib.pyplot")
add_stub("psutil")
add_stub("requests")

runpy.run_path({source!r}, run_name="__main__")
"""


class TestMCPStdioBoundary(unittest.TestCase):
    def setUp(self) -> None:
        if importlib.util.find_spec("mcp") is None:
            self.skipTest("mcp package not installed")
        self.proc = subprocess.Popen(
            [sys.executable, "-u", "-c", _server_bootstrap()],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self._events: queue.Queue[tuple[str, object]] = queue.Queue()
        self._reader = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader.start()

    def tearDown(self) -> None:
        if hasattr(self, "proc") and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        if hasattr(self, "proc"):
            for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
                if stream is not None:
                    stream.close()

    def _read_stdout(self) -> None:
        assert self.proc.stdout is not None
        for line in self.proc.stdout:
            text = line.strip()
            if not text:
                continue
            try:
                self._events.put(("message", json.loads(text)))
            except json.JSONDecodeError as exc:
                self._events.put(("decode_error", exc))
        self._events.put(("eof", None))

    def _send(self, message: dict) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def _read_response(self, request_id: int, timeout: float = 15.0) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            wait = max(0.1, deadline - time.time())
            try:
                kind, payload = self._events.get(timeout=wait)
            except queue.Empty:
                continue
            if kind == "message":
                message = payload
                if isinstance(message, dict) and message.get("id") == request_id:
                    return message
                continue
            if kind == "decode_error":
                self.fail(f"Failed to decode MCP server response: {payload}")
            if kind == "eof":
                stderr = ""
                if self.proc.stderr is not None:
                    stderr = self.proc.stderr.read()
                self.fail(f"MCP server exited unexpectedly. stderr:\n{stderr}")
        self.fail(f"Timed out waiting for MCP response id={request_id}")

    def _initialize(self) -> None:
        self._send({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "genesis-test", "version": "1"},
            },
        })
        init_response = self._read_response(1)
        self.assertIn("result", init_response)
        self._send({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        })

    def test_only_allowlisted_tools_are_exposed_over_stdio(self):
        self._initialize()
        self._send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        response = self._read_response(2)
        tool_names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(tool_names, ALLOWED)

    def test_denied_tool_call_fails_for_direct_mcp_client(self):
        self._initialize()
        self._send({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "add_int", "arguments": {"a": 2, "b": 3}},
        })
        allowed = self._read_response(3)
        self.assertFalse(allowed["result"].get("isError"))

        self._send({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "run_cmd", "arguments": {"cmd": ["whoami"]}},
        })
        denied = self._read_response(4)
        self.assertTrue(denied["result"].get("isError"))
        body = json.dumps(denied["result"]).lower()
        self.assertIn("unknown tool", body)


if __name__ == "__main__":
    unittest.main()
