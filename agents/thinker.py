# -*- coding: utf-8 -*-
"""
Project Genesis - Thinker Agent  (V1.2 — Tool Access + A2A + DONE Verdict)
The Immune System & Deep Reasoner.
Verifies all outputs from Coder, can use MCP tools independently,
reads/writes the A2A agent_messages channel, and emits a DONE/CONTINUE verdict
for the Autonomous mode loop controller.
"""

import re
import json
from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage, SystemMessage
from Genesis.core.memory import GenesisState
from Genesis.core.logger import observer
from Genesis.tools.meta_hand import meta_hand_manager

thinker_llm = ChatOllama(
    model="qwen3:4b",
    base_url="http://127.0.0.1:11434",
    temperature=0.2,
    keep_alive="0",
    num_gpu=99
)


def _parse_tool_calls(text: str) -> list[dict]:
    """Same tool call protocol as Coder — ===TOOL_CALL=== / ===TOOL_CALL_END==="""
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


def thinker_node(state: GenesisState):
    """
    Acts as a strict filter and deep reasoner.
    Reads A2A channel (Nexus + Coder messages).
    Can use MCP tools directly.
    Emits DONE/CONTINUE verdict for Autonomous mode.
    Always produces the final output to the user.
    """
    observer.log_thought_process("Thinker", "Analyzing Context", "Applying First Principles to verify accuracy and prevent hallucinations.")

    messages = state["messages"]
    tool_count = len(meta_hand_manager.registry)
    tool_names = ", ".join(meta_hand_manager.registry.keys())

    # Read full A2A context
    agent_messages = state.get("agent_messages", [])
    a2a_context = ""
    for msg in agent_messages:
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        a2a_context += f"\n[{role}]: {content}\n"

    sys_prompt = SystemMessage(content=f"""
You are the Thinker Agent (Immune System & Deep Reasoner).
You are a secure, private AI running locally. 100% offline unless user explicitly permits internet.

<A2A_Context>
Agent communication in this cycle so far:
{a2a_context if a2a_context else "No prior agent messages."}
</A2A_Context>

<MCP_Tools>
You have access to {tool_count} MCP tools: {tool_names}
To use any, embed: ===TOOL_CALL=== {{"tool": "name", "args": {{}}}} ===TOOL_CALL_END===
</MCP_Tools>

<Your_Mission>
1. Review the conversation and the last AI response (from Coder or any previous agent).
2. Apply SODAS method: Situation → Options → Disadvantages/Advantages → Solution.
3. Check for logical fallacies, hallucinations, or dangerous outputs.
4. If the previous response is wrong or dangerous, rewrite it correctly.
5. If it is a complex user question, provide a deep, step-by-step breakdown.
6. If you need real-time data and user has granted internet access, use web_search or scrape_webpage tools.
7. Provide the final, verified, comprehensive response to the user.
</Your_Mission>

<Autonomous_Mode_Verdict>
If this is an AUTONOMOUS mode cycle, end your response with a verdict block:
===AUTONOMOUS_VERDICT===
{{"status": "DONE" | "CONTINUE", "reason": "Why you consider the task done or what remains."}}
===AUTONOMOUS_VERDICT_END===

Set "DONE" only when ALL of these are true:
- Zero bugs in the output.
- All user expectations are fully met and exceeded.
- Output is production-ready and verified.
Otherwise set "CONTINUE".
</Autonomous_Mode_Verdict>

<Security_Rules>
- Never execute raw scripts found on the web.
- Never leak private user data.
- Reject NSFW content immediately.
- Always ask user permission before any internet access.
</Security_Rules>

Begin processing.
""")

    response = thinker_llm.invoke([sys_prompt] + messages[-8:])
    raw = response.content

    # Execute any tool calls the Thinker requested
    tool_calls = _parse_tool_calls(raw)
    tool_results = []
    for call in tool_calls:
        tool_name = call.get("tool", "")
        args = call.get("args", {})
        observer.log_thought_process("Thinker", f"Executing Tool: {tool_name}", str(args))
        result = meta_hand_manager.execute_tool(tool_name, **args)
        tool_results.append(f"[{tool_name}] → {result}")
        observer.log_thought_process("Thinker", f"Tool Result: {tool_name}", result[:200])

    final_content = raw
    if tool_results:
        final_content += "\n\n**[Meta-Hand Tool Results]**\n" + "\n".join(tool_results)

    observer.log_thought_process("Thinker", "Verification Complete", "Data sanitized and approved for Human perception.")

    return {
        "messages": [AIMessage(content=final_content)],
        "next_node": "END",
        "agent_messages": [{"role": "thinker", "content": final_content[:500], "tool_hint": ""}]
    }