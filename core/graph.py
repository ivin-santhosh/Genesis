# -*- coding: utf-8 -*-
"""
Project Genesis - The Connective Tissue (StateGraph)  V1.2
Wires all organs together into a cohesive, synchronous biological ecosystem.

New in V1.2:
- autonomous_node: A2A collaborative loop where Nexus manages Coder+Thinker iteratively.
- MCP tool reload: On every process_stimulus() call, reconnects to MCP and re-registers tools
  so newly added tools in mcp_tools.py are detected automatically.
- AUTONOMOUS conditional edge wired to autonomous_node.
"""

import re
import json
import asyncio
import os
import sys
from typing import List, Dict, Any

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_ollama import ChatOllama

from Genesis.core.memory import GenesisState, ContextCompressor
from Genesis.core.logger import observer
from Genesis.agents.nexus import nexus_node
from Genesis.agents.coder import coder_node
from Genesis.agents.thinker import thinker_node
from Genesis.tools.meta_hand import meta_hand_manager

# =========================================================
# MCP TOOL RELOAD ENGINE
# =========================================================
_mcp_client_ref = None   # Holds the live MultiServerMCPClient

def set_mcp_client(client):
    """Called from main.py after bootstrap to give graph a reference to reload from."""
    global _mcp_client_ref
    _mcp_client_ref = client

def reload_mcp_tools():
    """
    Re-fetches the tool list from the running MCP server and re-registers everything.
    Detects newly added tools automatically.
    Called before every process_stimulus() invocation.
    """
    global _mcp_client_ref
    if _mcp_client_ref is None:
        return

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Spyder/IPython environment — use nest_asyncio
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

    # Swap sys.stderr to devnull to prevent Spyder fake-stream crash
    import io
    _devnull = open(os.devnull, 'w')
    _orig_stderr = sys.stderr
    sys.stderr = _devnull
    try:
        fresh_tools = await _mcp_client_ref.get_tools()
        sys.stderr = _orig_stderr

        existing = set(meta_hand_manager.registry.keys())
        new_count = 0
        for t in fresh_tools:
            meta_hand_manager.registry[t.name] = t  # silent re-register
            if t.name not in existing:
                new_count += 1
                print(f"🆕 [Meta-Hand] NEW tool detected & loaded: {t.name}")

        if new_count > 0:
            observer.log_thought_process("System", "MCP Reload", f"{new_count} new tool(s) registered. Total: {len(meta_hand_manager.registry)}")
        else:
            observer.log_thought_process("System", "MCP Reload", f"All {len(fresh_tools)} tools verified current.")
    except Exception as e:
        sys.stderr = _orig_stderr
        observer.log_thought_process("System", "MCP Reload Error", str(e))
    finally:
        _devnull.close()


# =========================================================
# AUTONOMOUS NODE — A2A Collaborative Loop
# =========================================================
MAX_AUTONOMOUS_ITERATIONS = 10

nexus_llm_auto = ChatOllama(
    model="stark-enterprise:latest",
    base_url="http://127.0.0.1:11434",
    temperature=0.1,
    keep_alive="5m"
)
coder_llm_auto = ChatOllama(
    model="qwen2.5-coder:7b-instruct-q5_K_M",
    base_url="http://127.0.0.1:11434",
    temperature=0.0,
    keep_alive="0"
)
thinker_llm_auto = ChatOllama(
    model="qwen3:4b",
    base_url="http://127.0.0.1:11434",
    temperature=0.2,
    keep_alive="0"
)


def _extract_verdict(text: str) -> str | None:
    """Extracts DONE/CONTINUE from Thinker's ===AUTONOMOUS_VERDICT=== block."""
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
    """Execute any tool calls embedded in agent response. Returns appended tool results."""
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


def autonomous_node(state: GenesisState):
    """
    The A2A Collaborative Engine.
    Nexus (Manager) → Coder (Executor) → Thinker (Verifier) loop.
    Continues until Thinker emits DONE or MAX_AUTONOMOUS_ITERATIONS is reached.
    The user is the boss — their original request drives every iteration.
    """
    tool_manifest = meta_hand_manager.get_tool_descriptions()
    messages = state["messages"]
    iteration = state.get("autonomous_iteration_count", 0)
    a2a_log: List[Dict[str, Any]] = list(state.get("agent_messages", []))

    observer.log_thought_process("AUTONOMOUS", f"Iteration {iteration + 1}/{MAX_AUTONOMOUS_ITERATIONS}",
                                  "Starting collaborative A2A cycle.")

    # --- NEXUS: Plan this iteration ---
    a2a_summary = "\n".join(
        f"  [{m.get('role','?').upper()}]: {m.get('content','')[:300]}"
        for m in a2a_log[-6:]
    )
    nexus_prompt = [SystemMessage(content=f"""
You are Nexus, the Manager of the Autonomous Genesis Swarm.
You are in AUTONOMOUS collaborative mode — iteration {iteration + 1}.

LIVE TOOLS:
{tool_manifest}

A2A Log (recent):
{a2a_summary if a2a_summary else "First iteration — no prior A2A messages."}

Your job this iteration:
1. Review the user's request and A2A log.
2. Write a precise TASK DIRECTIVE for Coder — what to build/analyze/fix this iteration.
3. Write a VERIFICATION CRITERIA for Thinker — what passing looks like.
4. Keep it concise and actionable.

Output format:
===NEXUS_PLAN===
CODER_TASK: <exact task for Coder>
THINKER_CRITERIA: <exact verification criteria for Thinker>
===NEXUS_PLAN_END===
""")] + messages[-6:]

    nexus_raw = nexus_llm_auto.invoke(nexus_prompt).content
    observer.log_thought_process("AUTONOMOUS:Nexus", "Plan Issued", nexus_raw[:200])

    # Extract plan
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

    # --- CODER: Execute the task ---
    coder_prompt = [SystemMessage(content=f"""
You are Coder, the Execution Engine of the Autonomous Genesis Swarm.
Nexus has assigned you this task for iteration {iteration + 1}:

TASK: {coder_task}

LIVE MCP TOOLS (use them — embed calls using ===TOOL_CALL=== protocol):
{tool_manifest}

A2A Context:
{a2a_summary if a2a_summary else "First iteration."}

Produce the best possible output. Use tools as needed. Be exhaustive.
""")] + messages[-6:]

    coder_raw = coder_llm_auto.invoke(coder_prompt).content
    coder_final = _run_tools(coder_raw, "AUTONOMOUS:Coder")
    observer.log_thought_process("AUTONOMOUS:Coder", "Execution", coder_final[:200])
    a2a_log.append({"role": "coder", "content": coder_final[:500], "tool_hint": ""})

    # --- THINKER: Verify and emit verdict ---
    thinker_prompt = [SystemMessage(content=f"""
You are Thinker, the Verification Engine of the Autonomous Genesis Swarm.
Iteration {iteration + 1}. Nexus's verification criteria:

CRITERIA: {thinker_criteria}

Coder's output:
{coder_final[:2000]}

LIVE MCP TOOLS (use if verification requires them):
{tool_manifest}

1. Verify correctness, completeness, and safety against the criteria.
2. Identify any bugs, gaps, or unmet expectations.
3. Rewrite or supplement the output if needed.
4. Emit your verdict:

===AUTONOMOUS_VERDICT===
{{"status": "DONE" | "CONTINUE", "reason": "Why DONE or what still needs work."}}
===AUTONOMOUS_VERDICT_END===

Then provide the final complete response to the user.
""")] + messages[-4:] + [AIMessage(content=coder_final)]

    thinker_raw = thinker_llm_auto.invoke(thinker_prompt).content
    thinker_final = _run_tools(thinker_raw, "AUTONOMOUS:Thinker")
    observer.log_thought_process("AUTONOMOUS:Thinker", "Verification", thinker_final[:200])
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
        observer.log_thought_process("AUTONOMOUS", f"Iteration {new_iteration} → CONTINUE",
                                      "Thinker says more work needed. Looping back.")
        # Append Thinker's partial result to messages so next cycle has full context
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

# Stimulus enters the Brain
workflow.add_edge(START, "Nexus")

# The Brain routes the signal
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

# Autonomous loop — self-routes back to AUTONOMOUS or END
workflow.add_conditional_edges(
    "AUTONOMOUS",
    lambda state: state["next_node"],
    {
        "AUTONOMOUS": "AUTONOMOUS",
        "END": END
    }
)

# Coder always routes to Thinker for verification
workflow.add_edge("Coder", "Thinker")

# Thinker always finalizes to END
workflow.add_edge("Thinker", END)

ecosystem = workflow.compile()


def process_stimulus(user_input: str, current_state: GenesisState) -> GenesisState:
    """
    Main execution loop.
    1. Reloads MCP tools to detect any new tools added since last prompt.
    2. Compresses memory (Lungs).
    3. Resets A2A channel and autonomous counter for this prompt cycle.
    4. Invokes the graph.
    """
    # 1. Reload MCP tools — detect any new tools written to mcp_tools.py
    reload_mcp_tools()

    # 2. VRAM breathe
    current_state["messages"] = lungs.compress(current_state["messages"])

    # 3. Reset per-prompt state
    current_state["agent_messages"] = []
    current_state["autonomous_iteration_count"] = 0

    print("\n" + "="*50)
    observer.log_thought_process("System", "Stimulus Received", "Sending prompt through neural pathways...")

    # 4. Graph execution
    final_state = ecosystem.invoke(current_state)

    observer.save_state_trace(final_state, "END_OF_CYCLE")
    print("="*50 + "\n")
    return final_state