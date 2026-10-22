"""Security regression checks for the Genesis MCP tool registry.

Run: python -m unittest discover -s tests -v
These tests do not require an LLM, MCP server, or network.
"""
import unittest

from Genesis.tools.meta_hand import MetaHand, SafeExecSandbox


class TestSecurityBoundaries(unittest.TestCase):
    def setUp(self):
        self.manager = MetaHand()

    def test_runtime_code_synthesis_is_disabled(self):
        result = self.manager.mutate_tool("def hello(): return 'ok'", "hello")
        self.assertIn("BLOCKED", result)
        self.assertNotIn("hello", self.manager.registry)

    def test_persistent_code_append_is_disabled(self):
        result = self.manager.append_tool_to_mcp("@mcp.tool()\ndef injected(): return 1")
        self.assertIn("BLOCKED", result)

    def test_in_process_execution_fails_closed(self):
        ok, message = SafeExecSandbox().execute("def harmless(): return 1", "harmless")
        self.assertFalse(ok)
        self.assertIn("disabled", message.lower())

    def test_regular_registered_tool_still_works(self):
        self.manager.register_tool("add", lambda a, b: a + b)
        self.assertEqual(self.manager.execute_tool("add", a=2, b=3), "5")

    def test_unknown_tool_returns_explicit_error(self):
        result = self.manager.execute_tool("tool_that_does_not_exist")
        self.assertIn("ERROR", result)


if __name__ == "__main__":
    unittest.main()
