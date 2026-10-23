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
        """Fail closed: AST validation alone cannot isolate untrusted Python code.

        A future implementation must use an isolated process/container with
        explicit resource, filesystem, network and permission boundaries.
        """
        return False, (
            "[Sandbox Disabled] In-process agent-generated Python execution "
            "is unsafe and is disabled pending OS-enforced isolation."
        )


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
        print(f"[Meta-Hand] Tool registered: {tool_name}")

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
        Handles sync callables, async callables, and LangChain StructuredTool objects (sync & async).
        Returns a string result or error message.
        """
        from Genesis.core.security_gateway import security_gateway
        
        # Algorithmic Security Enforcer Check
        is_allowed, block_reason = security_gateway.enforce_algorithmic_rules(tool_name, kwargs)
        if not is_allowed:
            return block_reason

        tool = self.registry.get(tool_name)
        if tool is None:
            return f"[Meta-Hand] ERROR: Tool '{tool_name}' not found in registry."

        from Genesis.core.logger import audit_logger
        audit_logger.log("MetaHand", f"Executing Tool: {tool_name} | Args: {kwargs}")

        try:
            # 1. LangChain StructuredTool or objects with ainvoke / invoke
            if hasattr(tool, "ainvoke") or hasattr(tool, "invoke"):
                # Try ainvoke first if available (MCP tools from LangChain adapters are async StructuredTools)
                if hasattr(tool, "ainvoke"):
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            import nest_asyncio
                            nest_asyncio.apply()
                            result = loop.run_until_complete(tool.ainvoke(kwargs))
                        else:
                            result = loop.run_until_complete(tool.ainvoke(kwargs))
                        return str(result)
                    except Exception as aerr:
                        # Fallback to sync invoke if ainvoke fails
                        try:
                            result = tool.invoke(kwargs)
                            return str(result)
                        except Exception:
                            raise aerr

                # Fallback to invoke
                result = tool.invoke(kwargs)
                return str(result)

            # 2. Raw callables (sync or async)
            elif callable(tool):
                if asyncio.iscoroutinefunction(tool):
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        import nest_asyncio
                        nest_asyncio.apply()
                        result = loop.run_until_complete(tool(**kwargs))
                    else:
                        result = loop.run_until_complete(tool(**kwargs))
                else:
                    result = tool(**kwargs)
                    if asyncio.iscoroutine(result):
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            import nest_asyncio
                            nest_asyncio.apply()
                            result = loop.run_until_complete(result)
                        else:
                            result = loop.run_until_complete(result)
                return str(result)
            else:
                return f"[Meta-Hand] ERROR: '{tool_name}' is not callable."
        except Exception as e:
            return f"[Meta-Hand] TOOL EXECUTION ERROR ({tool_name}): {e}\n{traceback.format_exc()}"

    def append_tool_to_mcp(self, function_code: str) -> str:
        """Fail closed: agents may not persist executable Python source."""
        return (
            "[Meta-Hand] BLOCKED: Agent-generated changes to MCP server source "
            "are disabled. Submit reviewed code through version control."
        )

    def mutate_tool(self, source_code: str, function_name: str) -> str:
        """Fail closed until an actual isolated sandbox is implemented."""
        return (
            "[Meta-Hand] BLOCKED: Runtime code synthesis is disabled. "
            "Use version-controlled, reviewed tools instead."
        )


    def persist_system_instruction(self, role: str, instruction: str) -> str:
        """
        Persists a new or updated system instruction rule for an agent role ('nexus', 'coder', 'thinker', 'all')
        into config/system_instructions.json without error, persisting across sessions.
        """
        import os, json
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
        os.makedirs(config_dir, exist_ok=True)
        instr_file = os.path.join(config_dir, "system_instructions.json")

        current = {}
        if os.path.exists(instr_file):
            try:
                with open(instr_file, "r", encoding="utf-8") as f:
                    current = json.load(f)
            except Exception:
                current = {}

        role_key = role.lower()
        if role_key not in current:
            current[role_key] = []
        
        if instruction not in current[role_key]:
            current[role_key].append(instruction)

        try:
            with open(instr_file, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=2)
            return f"[Meta-Hand] SUCCESS: System instruction for '{role_key}' persisted successfully to system_instructions.json."
        except Exception as e:
            return f"[Meta-Hand] WRITE ERROR: {e}"


# Instantiate the global singleton
meta_hand_manager = MetaHand()