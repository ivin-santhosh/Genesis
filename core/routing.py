# -*- coding: utf-8 -*-
"""
Project Genesis - Reflex Router
The 'Spinal Reflex Arc'. 
Executes 0ms latency tasks without invoking the LLM to save power and time.
"""

import re
from datetime import datetime
from typing import Optional, Callable, Dict

class ReflexRouter:
    """
    Bypasses the Prefrontal Cortex (Nexus) for trivial intents.
    Returns immediate answers for basic commands.
    """
    def __init__(self):
        self.reflexes: Dict[re.Pattern, Callable] = {
            re.compile(r"^(what time is it|time|current time)\??$", re.IGNORECASE): self._get_time,
            re.compile(r"^(clear|reset memory|flush)\??$", re.IGNORECASE): self._flush_memory,
            re.compile(r"^(status|system status|health)\??$", re.IGNORECASE): self._get_status
        }
        
    def _get_time(self, query: str) -> str:
        return f"Current local time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
    def _flush_memory(self, query: str) -> str:
        return "COMMAND_FLUSH_MEMORY" # Signals orchestrator to clear State Space
        
    def _get_status(self, query: str) -> str:
        return "System Operational. VRAM optimal. Offline mode active."

    def evaluate(self, user_query: str) -> Optional[str]:
        """
        Checks if the query triggers a reflex. If True, returns the string response.
        If False, returns None, meaning it must be sent to the Nexus (LLM).
        """
        clean_query = user_query.strip()
        for pattern, action in self.reflexes.items():
            if pattern.search(clean_query):
                print(f"⚡ [Spinal Reflex] 0ms execution triggered for: '{clean_query}'")
                return action(clean_query)
        return None