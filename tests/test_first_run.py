"""First-run and local AI behavior contract tests, no external model required."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Genesis.runtime.chat import LocalAssistant
from Genesis.runtime.launcher import launch


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []
    def chat(self, messages, *, tools=True):
        self.calls.append((messages, tools))
        return next(self.responses)


class TestAssistant(unittest.TestCase):
    def test_simple_response(self):
        assistant = LocalAssistant(FakeClient([{"content": "Hello!"}]))
        self.assertEqual(assistant.ask("Hi"), "Hello!")
        self.assertEqual(len(assistant.history), 2)

    def test_allowlisted_tool_round_trip(self):
        client = FakeClient([
            {"content": "", "tool_calls": [{"function": {
                "name": "calculate", "arguments": {"expression": "2+3"}}}]},
            {"content": "The result is 5."}
        ])
        assistant = LocalAssistant(client)
        self.assertEqual(assistant.ask("Calculate 2+3"), "The result is 5.")
        self.assertEqual(assistant.tool_history[0]["data"]["value"], 5.0)
        tool_payload = client.calls[1][0][-1]
        self.assertEqual(tool_payload["role"], "tool")
        self.assertTrue(json.loads(tool_payload["content"])["ok"])

    def test_disallowed_tool_reports_failure(self):
        client = FakeClient([
            {"content": "", "tool_calls": [{"function": {
                "name": "run_cmd", "arguments": {"command": "whoami"}}}]},
            {"content": "I could not execute that operation."}
        ])
        assistant = LocalAssistant(client)
        self.assertIn("could not", assistant.ask("run a command"))
        self.assertFalse(assistant.tool_history[0]["ok"])

    def test_failed_request_does_not_commit_history(self):
        class OfflineClient:
            def chat(self, messages, *, tools=True):
                raise OSError("offline")
        assistant = LocalAssistant(OfflineClient())
        with self.assertRaises(OSError):
            assistant.ask("Hello")
        self.assertEqual(assistant.history, [])


class TestFirstRun(unittest.TestCase):
    def test_offline_interactive_mode_without_packages(self):
        inputs = iter(["/calc 8*3", "/demo", "/quit"])
        output = []
        with tempfile.TemporaryDirectory() as folder:
            with patch("Genesis.runtime.launcher.installed_models", return_value=[]):
                result = launch(state_file=str(Path(folder) / "state.db"),
                                input_fn=lambda prompt: next(inputs),
                                print_fn=output.append)
        self.assertEqual(result, 0)
        self.assertTrue(any("24.0" in line for line in output))
        self.assertTrue(any('"PASS"' in line for line in output))
        self.assertTrue(any("Offline commands are ready" in line for line in output))

    def test_installed_model_is_selected(self):
        inputs = iter(["/quit"])
        output = []
        with tempfile.TemporaryDirectory() as folder:
            with patch("Genesis.runtime.launcher.installed_models",
                       return_value=["model:latest"]):
                self.assertEqual(launch(state_file=str(Path(folder) / "data.db"),
                                        input_fn=lambda prompt: next(inputs),
                                        print_fn=output.append), 0)
        self.assertTrue(any("Local AI ready: model:latest" in line for line in output))


if __name__ == "__main__":
    unittest.main()
