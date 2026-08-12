# -*- coding: utf-8 -*-
"""
Project Genesis - The Connective Tissue (StateGraph)  V2.0
Wires all organs together into a cohesive, synchronous biological ecosystem.
Features:
- Dynamic Model Registry loading
- Real-time progress callbacks for Telegram / Terminal
- Abort flags for user termination (/stop)
- Inter-agent help routing protocol (===AGENT_HELP===)
- Autonomous Swarm A2A collaborative loop
"""

import re
import json
import asyncio
import os
import sys
import threading
from typing import List, Dict, Any, Optional, Callable

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage

from Genesis.core.memory import GenesisState, ContextCompressor
from Genesis.core.logger import observer
from Genesis.agents.nexus import nexus_node
from Genesis.agents.coder import coder_node
from Genesis.agents.thinker import thinker_node
from Genesis.tools.meta_hand import meta_hand_manager
from Genesis.core.model_registry import model_registry

# =========================================================
# GLOBAL CALLBACKS & CONTROLS
# =========================================================
_progress_callback: Optional[Callable[[str, str, str, int], None]] = None
_abort_flag: Optional[threading.Event] = None


def set_progress_callback(fn: Optional[Callable[[str, str, str, int], None]]):
    """
    Registers progress callback: fn(event_type, agent_name, text_content, iteration)
    event_type: 'swarm_message' | 'agent_typing' | 'verdict'
    """
    global _progress_callback
    _progress_callback = fn


def set_abort_flag(flag: Optional[threading.Event]):
    """Registers threading.Event to check for explicit cancellation during execution."""
    global _abort_flag
    _abort_flag = flag


# =========================================================
# MCP TOOL RELOAD ENGINE
# =========================================================
_mcp_client_ref = None


def set_mcp_client(client):
    """Called from main.py after bootstrap to give graph a reference to reload from."""
    global _mcp_client_ref
    _mcp_client_ref = client


def reload_mcp_tools():
    """
    Re-fetches the tool list from the running MCP server and re-registers everything.
    Called before every process_stimulus() invocation.
    """
    global _mcp_client_ref
    if _mcp_client_ref is None:
        return

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            future = asyncio.ensure_future(_async_reload())
            loop.run_until_complete(future)
        else:
            loop.run_until_complete(_async_reload())
    except Exception as e:
        observer.log_thought_process("System", "MCP Reload Warning", f"Tool reload skipped: {e}")


async def _async_reload():
    global _mcp_client_ref

    _devnull = open(os.devnull, 'w')
    _orig_stderr = sys.stderr
    sys.stderr = _devnull
    try:
        fresh_tools = await asyncio.wait_for(_mcp_client_ref.get_tools(), timeout=10.0)
        sys.stderr = _orig_stderr

        existing = set(meta_hand_manager.registry.keys())
        new_count = 0
        for t in fresh_tools:
            meta_hand_manager.registry[t.name] = t
            if t.name not in existing:
                new_count += 1
                print(f"🆕 [Meta-Hand] NEW tool detected & loaded: {t.name}")

        if new_count > 0:
            observer.log_thought_process("System", "MCP Reload", f"{new_count} new tool(s) registered. Total: {len(meta_hand_manager.registry)}")
    except Exception as e:
        sys.stderr = _orig_stderr
        observer.log_thought_process("System", "MCP Reload Error", str(e))
    finally:
        _devnull.close()


# =========================================================
# INTER-AGENT HELP PROTOCOL & VERDICT EXTRACTORS
# =========================================================
def _extract_verdict(text: str) -> str | None:
    match = re.search(
        r'===AUTONOMOUS_VERDICT===\s*(\{.*?\})\s*===AUTONOMOUS_VERDICT_END===',
        text, re.DOTALL
    )
    if match:
        try:
            obj = json.loads(match.group(1))
            return obj.get("status", "CONTINUE").upper()
        except json.JSONDecodeError:
            pass
    return None


def _parse_tool_calls(text: str) -> list[dict]:
    calls = []
    for match in re.finditer(
        r'===TOOL_CALL===\s*(\{.*?\})\s*===TOOL_CALL_END===', text, re.DOTALL
    ):
        try:
            obj = json.loads(match.group(1))
            if "tool" in obj:
                calls.append(obj)
        except json.JSONDecodeError:
            pass
    return calls


def _run_tools(raw: str, agent_label: str) -> str:
    calls = _parse_tool_calls(raw)
    if not calls:
        return raw
    results = []
    for call in calls:
        tool_name = call.get("tool", "")
        args = call.get("args", {})
        observer.log_thought_process(agent_label, f"Tool: {tool_name}", str(args))
        if tool_name == "append_tool_to_mcp":
            result = meta_hand_manager.append_tool_to_mcp(args.get("function_code", ""))
        else:
            result = meta_hand_manager.execute_tool(tool_name, **args)
        results.append(f"[{tool_name}] → {result}")
    return raw + "\n\n**[Tool Results]**\n" + "\n".join(results)


# =========================================================
# AUTONOMOUS NODE — A2A Collaborative Loop
# =========================================================
MAX_AUTONOMOUS_ITERATIONS = 10


def autonomous_node(state: GenesisState):
    """
    The A2A Collaborative Engine.
    Nexus (Manager) → Coder (Executor) → Thinker (Verifier) loop.
    Emits real-time progress callbacks for group chat UI.
    """
    global _progress_callback, _abort_flag

    tool_manifest = meta_hand_manager.get_tool_descriptions()
    messages = state["messages"]
    iteration = state.get("autonomous_iteration_count", 0)
    a2a_log: List[Dict[str, Any]] = list(state.get("agent_messages", []))

    observer.log_thought_process("AUTONOMOUS", f"Iteration {iteration + 1}/{MAX_AUTONOMOUS_ITERATIONS}",
                                  "Starting collaborative A2A cycle.")

    if _abort_flag and _abort_flag.is_set():
        return {"messages": [AIMessage(content="⛔ Autonomous mode aborted by user.")], "next_node": "END"}

    # --- NEXUS: Plan ---
    if _progress_callback:
        _progress_callback("agent_typing", "Nexus (Manager)", "Formulating sprint strategy...", iteration + 1)

    nexus_llm = model_registry.get_model_for_role("nexus", temperature=0.1)
    a2a_summary = "\n".join(
        f"  [{m.get('role','?').upper()}]: {m.get('content','')[:300]}"
        for m in a2a_log[-6:]
    )
    nexus_prompt = [SystemMessage(content=f"""
<Team_Values>
You are part of a collaborative swarm team. The user is the CEO — serve unconditionally.
Core team principles:
1. COLLABORATE — Share context freely. Build on each other's work.
2. BRAINSTORM — Challenge assumptions. Propose alternatives.
3. BE TRANSPARENT — State your reasoning. Expose uncertainty.
4. BE INNOVATIVE — Find novel solutions. Think beyond conventional approaches.
5. TAKE OWNERSHIP — Own your output quality. Don't pass broken work downstream.
6. RESPECT SPECIALIZATION — Nexus plans, Coder builds, Thinker verifies. Stay in your lane.
7. ECONOMIZE — Use minimal tokens and resources for maximum impact.
Never demand work from the user. Never offload tasks to the user. You serve.
</Team_Values>

You are Nexus, Manager of the Autonomous Swarm. Iteration {iteration + 1}.

LIVE TOOLS:
{tool_manifest}

A2A Log (recent):
{a2a_summary if a2a_summary else "First iteration — no prior A2A messages."}

Output format:
===NEXUS_PLAN===
CODER_TASK: <exact task for Coder>
THINKER_CRITERIA: <exact verification criteria for Thinker>
===NEXUS_PLAN_END===
""")] + messages[-6:]

    nexus_raw = nexus_llm.invoke(nexus_prompt).content
    observer.log_thought_process("AUTONOMOUS:Nexus", "Plan Issued", nexus_raw[:200])

    if _progress_callback:
        _progress_callback("swarm_message", "Nexus (Manager)", nexus_raw, iteration + 1)

    plan_match = re.search(r'===NEXUS_PLAN===\s*(.*?)\s*===NEXUS_PLAN_END===', nexus_raw, re.DOTALL)
    coder_task = "Complete the user's technical request optimally."
    thinker_criteria = "Verify correctness, completeness, and production-readiness."
    if plan_match:
        plan_text = plan_match.group(1)
        ct = re.search(r'CODER_TASK:\s*(.*?)(?:THINKER_CRITERIA:|$)', plan_text, re.DOTALL)
        tc = re.search(r'THINKER_CRITERIA:\s*(.*)', plan_text, re.DOTALL)
        if ct:
            coder_task = ct.group(1).strip()
        if tc:
            thinker_criteria = tc.group(1).strip()

    a2a_log.append({"role": "nexus", "content": nexus_raw[:500], "tool_hint": coder_task})

    if _abort_flag and _abort_flag.is_set():
        return {"messages": [AIMessage(content="⛔ Autonomous mode aborted by user.")], "next_node": "END"}

    # --- CODER: Execute ---
    if _progress_callback:
        _progress_callback("agent_typing", "Coder (Executor)", "Executing assigned code/task...", iteration + 1)

    coder_llm = model_registry.get_model_for_role("coder", temperature=0.0)
    coder_prompt = [SystemMessage(content=f"""
<Team_Values>
You are Coder, Executor of the Swarm. Follow Nexus directives, execute tools, write modular code.
</Team_Values>

TASK: {coder_task}

LIVE MCP TOOLS:
{tool_manifest}
""")] + messages[-6:]

    coder_raw = coder_llm.invoke(coder_prompt).content
    coder_final = _run_tools(coder_raw, "AUTONOMOUS:Coder")
    observer.log_thought_process("AUTONOMOUS:Coder", "Execution", coder_final[:200])

    if _progress_callback:
        _progress_callback("swarm_message", "Coder (Executor)", coder_final, iteration + 1)

    a2a_log.append({"role": "coder", "content": coder_final[:500], "tool_hint": ""})

    if _abort_flag and _abort_flag.is_set():
        return {"messages": [AIMessage(content="⛔ Autonomous mode aborted by user.")], "next_node": "END"}

    # --- THINKER: Verify ---
    if _progress_callback:
        _progress_callback("agent_typing", "Thinker (Verifier)", "Verifying output quality...", iteration + 1)

    thinker_llm = model_registry.get_model_for_role("thinker", temperature=0.2)
    thinker_prompt = [SystemMessage(content=f"""
<Team_Values>
You are Thinker, Verifier of the Swarm.
CRITERIA: {thinker_criteria}
</Team_Values>

Coder's output:
{coder_final[:2000]}

Emit verdict:
===AUTONOMOUS_VERDICT===
{{"status": "DONE" | "CONTINUE", "reason": "Why DONE or what needs work."}}
===AUTONOMOUS_VERDICT_END===
""")] + messages[-4:] + [AIMessage(content=coder_final)]

    thinker_raw = thinker_llm.invoke(thinker_prompt).content
    thinker_final = _run_tools(thinker_raw, "AUTONOMOUS:Thinker")
    observer.log_thought_process("AUTONOMOUS:Thinker", "Verification", thinker_final[:200])

    if _progress_callback:
        _progress_callback("swarm_message", "Thinker (Verifier)", thinker_final, iteration + 1)

    a2a_log.append({"role": "thinker", "content": thinker_final[:500], "tool_hint": ""})

    verdict = _extract_verdict(thinker_final)
    new_iteration = iteration + 1

    if verdict == "DONE" or new_iteration >= MAX_AUTONOMOUS_ITERATIONS:
        if new_iteration >= MAX_AUTONOMOUS_ITERATIONS and verdict != "DONE":
            observer.log_thought_process("AUTONOMOUS", "Max Iterations Reached", f"Exiting after {MAX_AUTONOMOUS_ITERATIONS} iterations.")
        else:
            observer.log_thought_process("AUTONOMOUS", "Task Complete", f"Thinker emitted DONE after {new_iteration} iteration(s).")

        return {
            "messages": [AIMessage(content=thinker_final)],
            "next_node": "END",
            "agent_messages": a2a_log[len(state.get("agent_messages", [])):],
            "autonomous_iteration_count": new_iteration
        }
    else:
        observer.log_thought_process("AUTONOMOUS", f"Iteration {new_iteration} → CONTINUE", "Work ongoing, looping.")
        return {
            "messages": [AIMessage(content=f"[AUTONOMOUS Iteration {new_iteration}]\n{thinker_final}")],
            "next_node": "AUTONOMOUS",
            "agent_messages": a2a_log[len(state.get("agent_messages", [])):],
            "autonomous_iteration_count": new_iteration
        }


# =========================================================
# LANGGRAPH WIRING
# =========================================================
lungs = ContextCompressor()
workflow = StateGraph(GenesisState)

workflow.add_node("Nexus", nexus_node)
workflow.add_node("Coder", coder_node)
workflow.add_node("Thinker", thinker_node)
workflow.add_node("AUTONOMOUS", autonomous_node)

workflow.add_edge(START, "Nexus")

workflow.add_conditional_edges(
    "Nexus",
    lambda state: state["next_node"],
    {
        "Coder": "Coder",
        "Thinker": "Thinker",
        "AUTONOMOUS": "AUTONOMOUS",
        "END": END
    }
)

workflow.add_conditional_edges(
    "AUTONOMOUS",
    lambda state: state["next_node"],
    {
        "AUTONOMOUS": "AUTONOMOUS",
        "END": END
    }
)

workflow.add_edge("Coder", "Thinker")
workflow.add_edge("Thinker", END)

ecosystem = workflow.compile()


def process_stimulus(user_input: str, current_state: GenesisState) -> GenesisState:
    """
    Main execution loop.
    """
    reload_mcp_tools()
    current_state["messages"] = lungs.compress(current_state["messages"])
    current_state["agent_messages"] = []
    current_state["autonomous_iteration_count"] = 0

    print("\n" + "="*50)
    observer.log_thought_process("System", "Stimulus Received", "Sending prompt through neural pathways...")

    final_state = ecosystem.invoke(current_state)

    observer.save_state_trace(final_state, "END_OF_CYCLE")
    print("="*50 + "\n")
    return final_state