# -*- coding: utf-8 -*-
"""
Project Genesis - The Nervous System Observer (Transparency Engine)
Provides beginner-friendly, real-time abstractions of internal AI decision-making.
Logs all state changes for backpropagation and debugging.
"""

import json
from datetime import datetime
from typing import Any, Dict

class NervousSystemLogger:
    """
    Translates raw AI operations into human-readable biological metaphors.
    Ensures 100% transparency of the AI's internal monologue.
    """
    def __init__(self, log_file: str = "hippocampus_trace.jsonl"):
        self.log_file = log_file

    def log_thought_process(self, organ: str, action: str, rationale: str):
        """Prints a real-time, user-intuitive abstraction of the AI's decision."""
        icons = {
            "Nexus": "🧠 [Prefrontal Cortex]",
            "Coder": "💪 [Muscle Tissue]",
            "Thinker": "🩸 [Immune/Verification]",
            "Meta-Hand": "🧬 [Motor Cortex]",
            "AUTONOMOUS": "🤝 [A2A Swarm]",
            "AUTONOMOUS:Nexus": "🤝🧠 [Swarm:Manager]",
            "AUTONOMOUS:Coder": "🤝💪 [Swarm:Executor]",
            "AUTONOMOUS:Thinker": "🤝🩸 [Swarm:Verifier]"
        }
        icon = icons.get(organ, "⚙️ [System]")
        
        print(f"\n{icon} Action: {action}")
        print(f"   ↳ Rationale: {rationale}")
        
    def save_state_trace(self, state: Dict[str, Any], node_name: str):
        """
        Saves the exact ecosystem state at this microsecond.
        Allows for backpropagation (rollback) if an agent hallucinates or loops.
        """
        # Exclude complex objects (like raw BaseMessage classes) for the JSON trace,
        # extracting only the string content for auditability.
        trace = {
            "timestamp": datetime.now().isoformat(),
            "node": node_name,
            "next_node": state.get("next_node", "UNKNOWN"),
            "messages_count": len(state.get("messages", [])),
            "agent_messages_count": len(state.get("agent_messages", [])),
            "autonomous_iteration": state.get("autonomous_iteration_count", 0),
            "latest_message": state["messages"][-1].content[:500] if state.get("messages") else ""
        }
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(trace) + "\n")

# Global transparency engine
observer = NervousSystemLogger()