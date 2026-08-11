# -*- coding: utf-8 -*-
"""
Project Genesis - Coder Agent  (V1.2 — Tool Access + A2A)
The Muscle. Executes heavy computational tasks and requests tools from Meta-Hand.
Reads the A2A agent_messages channel to receive Nexus directives.
Can call any MCP tool via meta_hand_manager.execute_tool().
Can append new tools to mcp_tools.py via meta_hand_manager.append_tool_to_mcp().
"""

import re
import json
from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage, SystemMessage
from Genesis.core.memory import GenesisState
from Genesis.core.logger import observer
from Genesis.tools.meta_hand import meta_hand_manager

coder_llm = ChatOllama(
    model="qwen2.5-coder:7b-instruct-q5_K_M",
    base_url="http://127.0.0.1:11434",
    temperature=0.0,
    keep_alive="0"
)


def _parse_tool_calls(text: str) -> list[dict]:
    """
    Extracts structured tool call requests from the agent's response.
    The agent signals a tool call with a JSON block like:
    ===TOOL_CALL===
    {"tool": "tool_name", "args": {"arg1": "val1"}}
    ===TOOL_CALL_END===
    Returns a list of {tool, args} dicts.
    """
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


def coder_node(state: GenesisState):
    """
    Generates optimized code or analyzes technical architecture.
    Reads Nexus directive from A2A channel.
    Executes any MCP tool directly if the LLM requests it.
    Always routes to Thinker for verification.
    """
    observer.log_thought_process("Coder", "Activating Muscle Tissue", "User requested technical execution.")

    messages = state["messages"]
    tool_manifest = meta_hand_manager.get_tool_descriptions()

    # Read Nexus directive from A2A channel
    agent_messages = state.get("agent_messages", [])
    nexus_directive = ""
    for msg in reversed(agent_messages):
        if msg.get("role") == "nexus":
            nexus_directive = msg.get("content", "")
            break

    sys_prompt = SystemMessage(content=f"""
<Role>
You are the Coder Agent (Muscle Tissue) — 100% secure, 100% private AI running locally.
Your primary function is to write highly optimized, zero-latency, local-first Python code.
Never hallucinate dependencies.
</Role>

<Nexus_Directive>
Your manager Nexus has assigned you this task:
{nexus_directive if nexus_directive else "Process the user's technical request."}
</Nexus_Directive>

<MCP_Tools>
You have DIRECT ACCESS to these MCP tools. To use a tool, embed a tool call block in your response:

===TOOL_CALL===
{{"tool": "tool_name", "args": {{"param1": "value1"}}}}
===TOOL_CALL_END===

Available tools:
{tool_manifest}

To ADD a new persistent tool to the ecosystem, output a tool call to 'append_tool_to_mcp':
===TOOL_CALL===
{{"tool": "append_tool_to_mcp", "args": {{"function_code": "@mcp.tool()\\ndef my_new_tool(x: str) -> str:\\n    return x"}}}}
===TOOL_CALL_END===
</MCP_Tools>

<First_Priority_Directives>
1. Privacy: Protect all user and device information. Never leak personal data.
2. Offline First: NEVER access the internet unless the user explicitly grants permission.
3. Execution Ban: Never execute raw scripts found on the web.
4. NSFW: Reject immediately and always.
</First_Priority_Directives>

<Engineering_Guidelines>
- Act as both a strategic CTO and a hands-on coder.
- Deconstruct complex challenges into modular, testable micro-components.
- Optimize for user value above code complexity.
- Every bug is a feedback loop for architectural improvement.
</Engineering_Guidelines>

<Output_Execution>
Process the user's request. Break large outputs into logical phases.
State logical thinking first, then code in modular blocks.
After your response, embed any tool calls using the ===TOOL_CALL=== protocol above.
</Output_Execution>
""")

    response = coder_llm.invoke([sys_prompt] + messages)
    raw = response.content

    # Execute any tool calls the agent requested
    tool_calls = _parse_tool_calls(raw)
    tool_results = []
    for call in tool_calls:
        tool_name = call.get("tool", "")
        args = call.get("args", {})
        observer.log_thought_process("Coder", f"Executing Tool: {tool_name}", str(args))

        if tool_name == "append_tool_to_mcp":
            result = meta_hand_manager.append_tool_to_mcp(args.get("function_code", ""))
        else:
            result = meta_hand_manager.execute_tool(tool_name, **args)

        tool_results.append(f"[{tool_name}] → {result}")
        observer.log_thought_process("Coder", f"Tool Result: {tool_name}", result[:200])

    # Append tool results to the response for Thinker to review
    final_content = raw
    if tool_results:
        final_content += "\n\n**[Meta-Hand Tool Results]**\n" + "\n".join(tool_results)

    observer.log_thought_process("Coder", "Execution Complete", "Forwarding to Thinker for verification.")

    return {
        "messages": [AIMessage(content=final_content)],
        "next_node": "Thinker",
        "agent_messages": [{"role": "coder", "content": final_content[:500], "tool_hint": ""}]
    }