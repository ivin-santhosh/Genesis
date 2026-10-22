"""Deterministic allow/deny tests for the agent tool execution boundary."""
import unittest
from Genesis.core.security_gateway import SecurityGateway
from Genesis.tools.meta_hand import MetaHand


class TestAgentBoundary(unittest.TestCase):
    def test_high_risk_operations_are_denied(self):
        for name in (
            "run_cmd", "custom_python_tool_run", "custom_python_tool_create",
            "soar_orchestrate", "fw_block_ip", "defender_scan_full",
            "persist_system_instruction", "append_tool_to_mcp",
        ):
            with self.subTest(name=name):
                allowed, reason = SecurityGateway.enforce_algorithmic_rules(name, {})
                self.assertFalse(allowed)
                self.assertIn("BLOCKED", reason)

    def test_case_insensitive_prefix_matching(self):
        allowed, _ = SecurityGateway.enforce_algorithmic_rules("PowerShell_Execute", {})
        self.assertFalse(allowed)

    def test_registry_does_not_execute_blocked_callables(self):
        manager = MetaHand()
        calls = []
        manager.register_tool("run_cmd", lambda command: calls.append(command))
        outcome = manager.execute_tool("run_cmd", command="echo bad")
        self.assertIn("BLOCKED", outcome)
        self.assertEqual(calls, [])

    def test_known_read_only_function_still_executes(self):
        manager = MetaHand()
        manager.register_tool("read_status", lambda: "healthy")
        self.assertEqual(manager.execute_tool("read_status"), "healthy")


if __name__ == "__main__":
    unittest.main()
