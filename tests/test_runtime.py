"""End-to-end deterministic workflow and recovery regressions."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Genesis.runtime.engine import WorkflowEngine
from Genesis.runtime.state import CheckpointStore
from Genesis.runtime.tools import execute_tool, tool_names


class TestTools(unittest.TestCase):
    def test_arithmetic(self):
        self.assertEqual(execute_tool("calculate", {"expression": "(2+3)*4"})["data"]["value"], 20)
        self.assertFalse(execute_tool("calculate", {"expression": "1/0"})["ok"])

    def test_code_execution_is_not_allowed(self):
        for expression in ("__import__('os').system('whoami')", "2 ** 9999",
                           "(1).__class__", "2 * (3 + 4)"):
            outcome = execute_tool("calculate", {"expression": expression})
            if expression == "2 * (3 + 4)":
                self.assertTrue(outcome["ok"])
            else:
                self.assertFalse(outcome["ok"])

    def test_tool_registry_is_explicit(self):
        self.assertNotIn("run_cmd", tool_names())
        self.assertNotIn("execute_python", tool_names())
        self.assertFalse(execute_tool("run_cmd", {"command": "ls"})["ok"])


class TestWorkflow(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "state.db"
        self.store = CheckpointStore(self.path)
        self.engine = WorkflowEngine(self.store)

    def tearDown(self):
        self.store.close()
        self.directory.cleanup()

    def test_complete_and_idempotent_terminal_result(self):
        task = self.engine.plan([{"tool": "calculate", "args": {"expression": "5+5"}},
                                 {"tool": "utc_time"}])
        result = self.engine.execute(task["task_id"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(len(result["results"]), 2)
        self.assertEqual(self.engine.execute(task["task_id"]), result)

    def test_failed_operation_halts(self):
        task = self.engine.plan([{"tool": "calculate", "args": {"expression": "1/0"}},
                                 {"tool": "utc_time"}])
        result = self.engine.execute(task["task_id"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["verdict"], "FAIL")

    def test_resume_from_disk(self):
        task = self.engine.plan([{"tool": "utc_time"}, {"tool": "calculate", "args": {"expression": "9-2"}}])
        paused = self.engine.execute(task["task_id"], max_new_steps=1)
        self.assertEqual(paused["status"], "paused")
        self.assertEqual(paused["step_index"], 1)
        self.store.close()
        self.store = CheckpointStore(self.path)
        self.engine = WorkflowEngine(self.store)
        result = self.engine.resume(task["task_id"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["step_index"], 2)

    def test_crash_after_dispatch_never_replays_silently(self):
        task = self.engine.plan([{"tool": "utc_time"}])
        task["status"] = "running"
        task["inflight"] = 0
        self.store.save(task["task_id"], task)
        result = self.engine.resume(task["task_id"])
        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("Interrupted", result["error"])

    def test_cancel_prevents_execution(self):
        task = self.engine.plan([{"tool": "utc_time"}])
        result = self.engine.cancel(task["task_id"])
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(self.engine.resume(task["task_id"])["status"], "cancelled")

    def test_unknown_or_oversized_tool_request_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.plan([{"tool": "run_cmd"}])
        with self.assertRaises(ValueError):
            self.engine.plan([{"tool": "utc_time"}] * 13)
        with self.assertRaises(ValueError):
            self.engine.resume("missing")

    def test_duplicate_task_id_rejected(self):
        self.engine.plan([{"tool": "utc_time"}], task_id="same")
        with self.assertRaises(ValueError):
            self.engine.plan([{"tool": "utc_time"}], task_id="same")


if __name__ == "__main__":
    unittest.main()
