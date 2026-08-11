# -*- coding: utf-8 -*-
"""
Project Genesis - Meta-Hand (Motor Cortex & Sandbox)
Manages the O(1) Tool Registry and the Safe Execution Sandbox for dynamic mutations.
Provides:
  - get_tool_descriptions()   : Live markdown manifest injected into every agent's prompt
  - execute_tool()            : Directly invoke any MCP tool by name with kwargs
  - append_tool_to_mcp()      : Write a new @mcp.tool() block to mcp_tools.py
"""

import ast
import types
import asyncio
import inspect
import traceback
from typing import Callable, Dict, Any, Tuple, Optional


class SafeExecSandbox:
    """
    The Immune System Quarantine.
    Prevents dynamically generated code from executing destructive commands.
    """
    def __init__(self):
        self.banned_nodes = (ast.Delete, ast.ImportFrom)
        self.banned_names = {'os', 'sys', 'subprocess', 'shutil', 'eval', 'exec', 'open'}

    def _verify_ast(self, source_code: str) -> bool:
        try:
            tree = ast.parse(source_code)
            for node in ast.walk(tree):
                if isinstance(node, self.banned_nodes):
                    raise ValueError(f"Banned operation detected: {type(node).__name__}")
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in self.banned_names:
                            raise ValueError(f"Banned import detected: {alias.name}")
                if isinstance(node, ast.Name) and node.id in self.banned_names:
                    raise ValueError(f"Banned reference detected: {node.id}")
            return True
        except SyntaxError as e:
            raise ValueError(f"Syntax Error in generated code: {e}")

    def execute(self, source_code: str, function_name: str) -> Tuple[bool, Any]:
        try:
            self._verify_ast(source_code)
            safe_globals = {'__builtins__': __builtins__}
            safe_locals = {}
            exec(source_code, safe_globals, safe_locals)
            if function_name not in safe_locals:
                return False, f"Function '{function_name}' not found in compiled code."
            return True, safe_locals[function_name]
        except Exception as e:
            return False, f"[Sandbox Violation] {str(e)}\n{traceback.format_exc()}"


class MetaHand:
    """
    The Motor Cortex. Maintains O(1) hash map of capabilities (MCP tool objects).
    Provides tool descriptions for agent prompts and direct tool execution.
    """
    def __init__(self):
        self.registry: Dict[str, Any] = {}   # tool_name -> LangChain StructuredTool
        self.sandbox = SafeExecSandbox()

    def register_tool(self, tool_name: str, tool_obj: Any):
        """Binds a new capability to muscle memory."""
        self.registry[tool_name] = tool_obj
        print(f"🧬 [Meta-Hand] Muscle memory updated. Tool loaded: {tool_name}")

    def get_tool(self, tool_name: str) -> Optional[Any]:
        """O(1) Dictionary lookup. Zero latency."""
        return self.registry.get(tool_name, None)

    def get_tool_descriptions(self) -> str:
        """
        Returns a formatted markdown string of all available tools.
        Injected into every agent's system prompt on every call so they
        always know the live, up-to-date registry.
        """
        if not self.registry:
            return "*(No MCP tools currently registered)*"

        lines = []
        for name, tool in self.registry.items():
            desc = ""
            # LangChain StructuredTool has .description; raw callables may have __doc__
            if hasattr(tool, "description"):
                desc = (tool.description or "").strip().split("\n")[0]
            elif callable(tool) and tool.__doc__:
                desc = tool.__doc__.strip().split("\n")[0]
            lines.append(f"- **`{name}`**: {desc}")

        return "\n".join(lines)

    def execute_tool(self, tool_name: str, **kwargs) -> str:
        """
        Directly invoke an MCP tool by name. Called by agents to USE a tool.
        Handles both sync callables and LangChain StructuredTool objects.
        Returns a string result or error message.
        """
        tool = self.registry.get(tool_name)
        if tool is None:
            return f"[Meta-Hand] ERROR: Tool '{tool_name}' not found in registry."

        try:
            # LangChain tools use .invoke() or are directly callable
            if hasattr(tool, "invoke"):
                result = tool.invoke(kwargs)
            elif callable(tool):
                result = tool(**kwargs)
                if asyncio.iscoroutine(result):
                    loop = asyncio.get_event_loop()
                    result = loop.run_until_complete(result)
            else:
                return f"[Meta-Hand] ERROR: '{tool_name}' is not callable."

            return str(result)
        except Exception as e:
            return f"[Meta-Hand] TOOL EXECUTION ERROR ({tool_name}): {e}\n{traceback.format_exc()}"

    def append_tool_to_mcp(self, function_code: str) -> str:
        """
        Appends a new @mcp.tool() decorated function to tools/mcp_tools.py.
        This persists the new tool so it is loaded on the NEXT MCP reload cycle.
        The function_code must be a complete, valid Python function string.
        Returns a status message.
        """
        import os
        mcp_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "tools", "mcp_tools.py"
        )

        if not os.path.exists(mcp_path):
            return f"[Meta-Hand] ERROR: mcp_tools.py not found at {mcp_path}"

        # Validate syntax before writing
        try:
            ast.parse(function_code)
        except SyntaxError as e:
            return f"[Meta-Hand] SYNTAX ERROR in new tool code: {e}"

        # Ensure the @mcp.tool() decorator is present
        stripped = function_code.strip()
        if not stripped.startswith("@mcp.tool"):
            function_code = "@mcp.tool()\n" + function_code

        try:
            with open(mcp_path, "a", encoding="utf-8") as f:
                f.write("\n\n# --- AGENT-GENERATED TOOL ---\n")
                f.write(function_code.strip())
                f.write("\n")
            return f"[Meta-Hand] SUCCESS: New tool appended to mcp_tools.py. It will be available after the next MCP reload."
        except Exception as e:
            return f"[Meta-Hand] WRITE ERROR: {e}"

    def mutate_tool(self, source_code: str, function_name: str) -> str:
        """
        In-process tool synthesis via sandbox (for immediate, ephemeral tools).
        For persistent tools, use append_tool_to_mcp() instead.
        """
        print(f"🧪 [Meta-Hand] Synthesizing new capability: {function_name}...")
        success, result = self.sandbox.execute(source_code, function_name)
        if success:
            self.register_tool(function_name, result)
            return f"SUCCESS: Capability '{function_name}' synthesized and ready for O(1) deployment."
        else:
            return f"IMMUNE REJECTION: Tool synthesis failed.\n{result}"


# Instantiate the global singleton
meta_hand_manager = MetaHand()