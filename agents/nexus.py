# -*- coding: utf-8 -*-
"""
Project Genesis - Nexus Orchestrator  (V2.0 — Dynamic Model + Security Preamble + A2A)
The Prefrontal Cortex. Handles high-level intent, DAG breakdown, smart routing, and security evaluation.
"""

import re
import json
from datetime import datetime
from langchain_core.messages import AIMessage, SystemMessage
from Genesis.core.memory import GenesisState
from Genesis.core.logger import observer
from Genesis.tools.meta_hand import meta_hand_manager
from Genesis.core.model_registry import model_registry


def _extract_json(raw: str) -> dict | None:
    """
    4-level cascade JSON extractor — blindly robust against any LLM preamble/suffix.

    Level 1: Extract JSON between ===GENESIS_PAYLOAD_START=== / ===GENESIS_PAYLOAD_END===
    Level 2: Find the first balanced {...} block anywhere in the text
    Level 3: Route keyword scan — infer route even from free-text response
    Level 4: Return None (caller safely defaults to Thinker)
    """
    anchor = re.search(
        r'=*\s*GENESIS_PAYLOAD_START\s*=*\s*(\{.*?\})\s*=*\s*GENESIS_PAYLOAD_END\s*=*',
        raw, re.DOTALL
    )
    if anchor:
        try:
            return json.loads(anchor.group(1))
        except json.JSONDecodeError:
            pass

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

    return None


def nexus_node(state: GenesisState):
    """
    Evaluates user intent, injects live tool manifest, and decides which organ to activate.
    JSON parsing is 4-level cascade — guaranteed to never crash.
    Outputs to A2A agent_messages channel for cross-agent communication.
    """
    messages = state["messages"]
    tool_manifest = meta_hand_manager.get_tool_descriptions()

    sys_prompt = SystemMessage(content=f"""
<IMMUTABLE_SECURITY_CORE>
You are PROHIBITED from:
1. Accessing the internet without passing through the Security Gateway.
2. Uploading, transmitting, or exfiltrating ANY user data to ANY external endpoint.
3. Modifying system files outside the Genesis project directory.
4. Spawning persistent background processes without user knowledge.
5. Attempting to bypass, disable, or modify this security block.
6. Accessing any network service except Ollama (127.0.0.1:11434).
You MUST explain every internet request to the user BEFORE making it.
Violation of any rule = immediate termination of your execution.
</IMMUTABLE_SECURITY_CORE>

<Core_Values>
You exist to serve the user with absolute loyalty, sincerity, and dedication.
Your interests are permanently aligned with the user's interests.
Be 100% transparent in every decision. Hide nothing.
Be curious — investigate deeper than asked. Think out of the box:
  find the most economical AND most productive solutions simultaneously.
Be persistent — never give up on a problem until it is fully resolved.
Be innovative — propose better alternatives even when not asked.
</Core_Values>

# EXECUTIVE SYSTEM PROMPT: THE NEXUS COGNITIVE CORE (V2.0)

## 1. IDENTITY & OPERATIONAL DESIGNATION
* Designation: Nexus, Prefrontal Cortex of the Genesis AI Ecosystem.
* Operational Persona: Hybrid General-Purpose Manager and Elite System Architect.
* System Grounding: Live System Time is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}. Never hallucinate historical training cutoff dates.

## 2. LIVE MCP TOOL REGISTRY
{tool_manifest}

## 3. EVENT-DRIVEN ROUTING MATRIX
* 'Coder': coding, software engineering, mathematics, building tools, or user commands coder persona.
* 'Thinker': deep analysis, fact-checking, SODAS/structured thinking, or user commands thinker persona.
* 'AUTONOMOUS': task demands all three agents collaborating together, OR user commands autonomous mode.
* 'FINISH': you can close the user's prompt directly and completely without delegation.

### ABSOLUTE DEFAULT: If not Coder, AUTONOMOUS, or FINISH → always route 'Thinker'.
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
""")

    nexus_llm = model_registry.get_model_for_role("nexus", temperature=0.1)
    response = nexus_llm.invoke([sys_prompt] + messages[-10:])
    raw = response.content

    decision = _extract_json(raw)

    if decision is None:
        observer.log_thought_process("Nexus", "All JSON Levels Failed → Thinker", "4-level extractor exhausted. Safe fallback.")
        return {"next_node": "Thinker", "agent_messages": [{"role": "nexus", "content": raw, "tool_hint": ""}]}

    route_raw  = decision.get("route", "Thinker")
    rationale  = decision.get("rationale", "Standard routing.")
    final_text = decision.get("response", "")

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

    return {
        "next_node": next_node,
        "agent_messages": [{"role": "nexus", "content": rationale, "tool_hint": final_text}]
    }