"""MCP exposure policy regression tests without external services."""
import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MCP_SOURCE = ROOT / "tools" / "mcp_tools.py"


class TestMCPServerExposure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = ast.parse(MCP_SOURCE.read_text(encoding="utf-8"))
        cls.functions = {node.name: node for node in ast.walk(cls.tree)
                         if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        assignments = [node for node in cls.tree.body if isinstance(node, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == "_MCP_PUBLIC_ALLOWLIST"
                               for t in node.targets)]
        assert len(assignments) == 1
        cls.allowed = set(ast.literal_eval(assignments[0].value.args[0]))

    def test_allowlist_contains_only_known_functions(self):
        self.assertTrue(self.allowed)
        self.assertTrue(self.allowed.issubset(self.functions.keys()))

    def test_sensitive_functions_not_exposed(self):
        banned = {"run_cmd", "run_powershell", "fw_block_ip",
                  "firewall_block_ip", "custom_python_tool_run",
                  "custom_python_tool_create", "custom_dsl_tool_run",
                  "generate_soc_report", "defender_scan_full",
                  "_run_python_tool", "_write_json_file"}
        self.assertFalse(banned.intersection(self.allowed))

    def test_registration_is_conditional(self):
        wrapper = next(node for node in self.tree.body if isinstance(node, ast.ClassDef)
                       and node.name == "_SafeToolRegistry")
        source = ast.get_source_segment(MCP_SOURCE.read_text(encoding="utf-8"), wrapper)
        self.assertIn("function.__name__ not in _MCP_PUBLIC_ALLOWLIST", source)
        self.assertIn("return function", source)

    def test_public_tools_are_decorated(self):
        decorated = set()
        for node in self.tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if any(isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)
                       and dec.func.attr == "tool" for dec in node.decorator_list):
                    decorated.add(node.name)
        self.assertTrue(self.allowed.issubset(decorated))


if __name__ == "__main__":
    unittest.main()
