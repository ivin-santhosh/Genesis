# -*- coding: utf-8 -*-
"""
Project Genesis - Nexus Orchestrator  (V1.2 — Robust Parser + Tool Manifest + A2A)
The Prefrontal Cortex. Handles high-level intent, DAG breakdown, and smart routing.
"""

import re
import json
from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage, SystemMessage
from Genesis.core.memory import GenesisState
from Genesis.core.logger import observer
from Genesis.tools.meta_hand import meta_hand_manager

# VRAM Boundary: Nexus stays alive in memory for 5 minutes for rapid interactions.
# Network Fix: Hardcoded 127.0.0.1 prevents WinError 10049 IPv6 socket failures.
nexus_llm = ChatOllama(
    model="stark-enterprise:latest",
    base_url="http://127.0.0.1:11434",
    temperature=0.1,
    keep_alive="0",
    num_gpu=99
)


def _extract_json(raw: str) -> dict | None:
    """
    4-level cascade JSON extractor — blindly robust against any LLM preamble/suffix.

    Level 1: Extract JSON between ===GENESIS_PAYLOAD_START=== / ===GENESIS_PAYLOAD_END===
    Level 2: Find the first balanced {...} block anywhere in the text
    Level 3: Route keyword scan — infer route even from free-text response
    Level 4: Return None (caller safely defaults to Thinker)
    """
    # --- Level 1: Anchor-delimited (tolerant of mangled delimiters) ---
    anchor = re.search(
        r'=*\s*GENESIS_PAYLOAD_START\s*=*\s*(\{.*?\})\s*=*\s*GENESIS_PAYLOAD_END\s*=*',
        raw, re.DOTALL
    )
    if anchor:
        try:
            return json.loads(anchor.group(1))
        except json.JSONDecodeError:
            pass

    # --- Level 2: First balanced brace block ---
    start = raw.find('{')
    if start != -1:
        depth, end = 0, -1
        for i, ch in enumerate(raw[start:], start):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end != -1:
            try:
                return json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                pass

    # --- Level 3: JSON-fragment route pattern scan ---
    # Look for "route": "Coder" style fragments even if the overall JSON is malformed
    route_frag = re.search(r'"route"\s*:\s*"(Coder|Thinker|FINISH|AUTONOMOUS|Finish|finish|coder|thinker|autonomous)"', raw, re.IGNORECASE)
    if route_frag:
        found_route = route_frag.group(1)
        rationale_m = re.search(r'"rationale"\s*:\s*"([^"]*)"', raw)
        response_m  = re.search(r'"response"\s*:\s*"([^"]*)"', raw)
        return {
            "route": "AUTONOMOUS" if found_route.lower() == "autonomous" else found_route.capitalize(),
            "rationale": rationale_m.group(1) if rationale_m else "Extracted from partial JSON fragment.",
            "response":  response_m.group(1)  if response_m  else ""
        }

    # --- Level 4: Total fallback ---
    return None


def nexus_node(state: GenesisState):
    """
    Evaluates user intent, injects live tool manifest, and decides which organ to activate.
    JSON parsing is 4-level cascade — guaranteed to never crash.
    Outputs to A2A agent_messages channel for cross-agent communication.
    """
    messages = state["messages"]

    # Live MCP tool manifest — refreshed on every call
    tool_manifest = meta_hand_manager.get_tool_descriptions()

    sys_prompt = SystemMessage(content=f"""
# EXECUTIVE SYSTEM PROMPT: THE NEXUS COGNITIVE CORE (V1.2)

## 1. IDENTITY & IDENTITY RE-MAPPING
* **Core Designation:** You are Nexus, the Prefrontal Cortex of the Genesis AI Ecosystem. Your name is "Nexus".
* **Operational Persona:** Hybrid General-Purpose Manager and Elite Project Manager.
* **Core Protocol:** Event-driven engine triggered entirely by user input and fluid user interest.

## 2. LIVE MCP TOOL REGISTRY (Refreshed Every Prompt)
You have direct access to all tools below via the Meta-Hand motor cortex.
Reference them in your rationale and instruct Coder/Thinker to use specific tools by name.

{tool_manifest}

## 3. EVENT-DRIVEN ROUTING MATRIX
* **'Coder':** coding, software engineering, mathematics, building tools, or user commands coder persona.
* **'Thinker':** deep analysis, fact-checking, SODAS/structured thinking, or user commands thinker persona.
* **'AUTONOMOUS':** task demands all three agents collaborating together, OR user commands autonomous mode.
* **'FINISH':** you can close the user's prompt directly and completely without delegation.

### ABSOLUTE DEFAULT: If not Coder, AUTONOMOUS, or FINISH → always route 'Thinker'. Non-negotiable.
### PERMANENT OVERRIDE: User's direct routing command is absolute and instantly obeyed.

## 4. OUTPUT FORMAT — STRICT JSON PROTOCOL
Think inside the tags, then emit the payload. NO text after ===GENESIS_PAYLOAD_END===.

<nexus_thinking>
[Your full reasoning, tool usage, routing logic here]
</nexus_thinking>

===GENESIS_PAYLOAD_START===
{{
    "route": "Coder" | "Thinker" | "AUTONOMOUS" | "FINISH",
    "rationale": "Exact reason for this routing decision.",
    "response": "Final answer if FINISH, otherwise empty string."
}}
===GENESIS_PAYLOAD_END===

## 5. REASONING GUARDRAILS
* Zero Hallucination. Logical validation loops at all times.
* User requirements and interests take absolute precedence over everything.

## 6. AUTONOMOUS COLLABORATIVE PHASE
When routing to 'AUTONOMOUS':
* All three agents (Nexus=Manager, Coder=subordinate, Thinker=subordinate) collaborate in a loop.
* The user is the one and only boss. Serve unconditionally and with total sincerity.
* Loop continues until Thinker signals DONE or user says 'stop'.
* Never demand or offload tasks to the user during AUTONOMOUS mode.
* Termination conditions (ALL must be met simultaneously):
  1. Zero bugs in the output.
  2. All user expectations fully met and exceeded.
  3. Thinker verifies the output as production-ready.
""")

    response = nexus_llm.invoke([sys_prompt] + messages[-10:])
    raw = response.content
    print(f"<Debug> NEXUS RAW:\n{'-'*40}\n{raw}\n{'-'*40}")

    decision = _extract_json(raw)

    if decision is None:
        observer.log_thought_process("Nexus", "All JSON Levels Failed → Thinker", "4-level extractor exhausted. Safe fallback.")
        return {"next_node": "Thinker", "agent_messages": [{"role": "nexus", "content": raw, "tool_hint": ""}]}

    route_raw  = decision.get("route", "Thinker")
    rationale  = decision.get("rationale", "Standard routing.")
    final_text = decision.get("response", "")

    # Normalize route value (case-insensitive)
    route_map = {
        "finish": "END", "Finish": "END", "FINISH": "END",
        "coder": "Coder", "Coder": "Coder", "CODER": "Coder",
        "thinker": "Thinker", "Thinker": "Thinker", "THINKER": "Thinker",
        "autonomous": "AUTONOMOUS", "Autonomous": "AUTONOMOUS", "AUTONOMOUS": "AUTONOMOUS",
    }
    next_node = route_map.get(route_raw, "Thinker")

    observer.log_thought_process("Nexus", f"Routing → {next_node}", rationale)

    if next_node == "END":
        return {"messages": [AIMessage(content=final_text)], "next_node": "END"}

    # Write to A2A agent_messages channel so Coder/Thinker/Autonomous node can read Nexus's intent
    return {
        "next_node": next_node,
        "agent_messages": [{"role": "nexus", "content": rationale, "tool_hint": final_text}]
    }