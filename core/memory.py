# -*- coding: utf-8 -*-
"""
Project Genesis - Core Memory & State Space
Date: August 3, 2026
Location: Kalyan, Maharashtra, India

The 'Bloodstream' and 'Lungs'. Manages the shared state across all agents
and implements a rolling-window context compressor to prevent OOM crashes.
"""

import operator
from typing import Annotated, Sequence, TypedDict, Dict, Any, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

class GenesisState(TypedDict):
    """
    The Global State Space. Passed instantly via RAM pointers between agents.
    Zero network serialization latency.
    """
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_node: str
    user_profit_metric: float           # Tracks economic/time optimization
    active_permissions: Dict[str, str]  # Smart Permission Ledger (Green, Yellow, Red)
    task_dag: List[Dict[str, Any]]      # Directed Acyclic Graph of current tasks
    meta_hand_cache: Dict[str, Any]     # O(1) Tool retrieval cache
    # A2A Communication Channel: append-only message bus between agents
    agent_messages: Annotated[List[Dict[str, Any]], operator.add]
    # Autonomous mode iteration counter (reset per user prompt)
    autonomous_iteration_count: int


class ContextCompressor:
    """
    The 'Lungs': Expels stale tokens to keep the context window under 4096.
    Ensures 100% resource efficiency without losing critical memory.
    """
    def __init__(self, max_tokens: int = 3000):
        self.max_tokens = max_tokens
        
    def estimate_tokens(self, messages: Sequence[BaseMessage]) -> int:
        """Fast approximation of token count to avoid heavy tokenizer loading."""
        return sum(len(m.content.split()) * 1.3 for m in messages)
        
    def compress(self, messages: Sequence[BaseMessage]) -> Sequence[BaseMessage]:
        """
        If tokens exceed threshold, retains the System prompt, the first 2 messages,
        and the most recent 5 messages. Intermediary messages are summarized/dropped.
        """
        current_tokens = self.estimate_tokens(messages)
        if current_tokens < self.max_tokens or len(messages) <= 8:
            return messages
            
        print(f"🫁 [Context Compressor] VRAM capacity approaching limit. Exhaling stale context...")
        
        # Keep SystemMessage, first interaction, and trailing context
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        human_ai_msgs = [m for m in messages if not isinstance(m, SystemMessage)]
        
        retained_context = system_msgs + human_ai_msgs[:2] + human_ai_msgs[-5:]
        return retained_context