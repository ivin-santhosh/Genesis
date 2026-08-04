# -*- coding: utf-8 -*-
"""
Project Genesis - Meta-Hand (Motor Cortex & Sandbox)
Manages the O(1) Tool Registry and the Safe Execution Sandbox for dynamic mutations.
"""

import ast
import types
import traceback
from typing import Callable, Dict, Any, Tuple

class SafeExecSandbox:
    """
    The Immune System Quarantine.
    Prevents dynamically generated code from executing destructive commands.
    """
    def __init__(self):
        # Nodes that are explicitly banned to prevent system damage
        self.banned_nodes = (ast.Delete, ast.ImportFrom)
        self.banned_names = {'os', 'sys', 'subprocess', 'shutil', 'eval', 'exec', 'open'}

    def _verify_ast(self, source_code: str) -> bool:
        """Parses the code into an AST and checks for malicious/dangerous patterns."""
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
        """Safely compiles and extracts a function from a source string."""
        try:
            self._verify_ast(source_code)
            
            # Isolated namespace
            safe_globals = {'__builtins__': __builtins__}
            safe_locals = {}
            
            exec(source_code, safe_globals, safe_locals)
            
            if function_name not in safe_locals:
                return False, f"Function '{function_name}' not found in compiled code."
                
            extracted_func = safe_locals[function_name]
            return True, extracted_func
            
        except Exception as e:
            return False, f"[Sandbox Violation] {str(e)}\n{traceback.format_exc()}"

class MetaHand:
    """
    The Motor Cortex. Maintains O(1) hash map of capabilities.
    Instantly returns tools or triggers asynchronous mutation if missing.
    """
    def __init__(self):
        self.registry: Dict[str, Callable] = {}
        self.sandbox = SafeExecSandbox()
        
    def register_tool(self, tool_name: str, func: Callable):
        """Binds a new capability to the muscle memory."""
        self.registry[tool_name] = func
        print(f"🧬 [Meta-Hand] Muscle memory updated. Tool loaded: {tool_name}")

    def get_tool(self, tool_name: str) -> Callable:
        """O(1) Dictionary lookup. Zero latency."""
        return self.registry.get(tool_name, None)

    def mutate_tool(self, source_code: str, function_name: str) -> str:
        """
        Called by the Nexus/Coder when a new capability is needed.
        Runs through the sandbox. If successful, registers it instantly.
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