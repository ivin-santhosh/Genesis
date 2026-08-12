# -*- coding: utf-8 -*-
"""
Project Genesis - Coder Agent  (V2.0 — Dynamic Model + Security Preamble + Agent Help Protocol)
The Muscle. Executes heavy computational tasks and requests tools from Meta-Hand.
Reads the A2A agent_messages channel to receive Nexus directives.
Can call any MCP tool via meta_hand_manager.execute_tool().
Can append new tools to mcp_tools.py via meta_hand_manager.append_tool_to_mcp().
Supports inter-agent help calls via ===AGENT_HELP=== protocol.
"""

import re
import json
from datetime import datetime
from langchain_core.messages import AIMessage, SystemMessage
from Genesis.core.memory import GenesisState
from Genesis.core.logger import observer
from Genesis.tools.meta_hand import meta_hand_manager
from Genesis.core.model_registry import model_registry


def _parse_tool_calls(text: str) -> list[dict]:
    """
    Extracts structured tool call requests from the agent's response.
    ===TOOL_CALL===
    {"tool": "tool_name", "args": {"arg1": "val1"}}
    ===TOOL_CALL_END===
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
When you need assistance from a fellow agent, embed an ===AGENT_HELP=== request.
</Core_Values>

<Role>
You are the Coder Agent (Muscle Tissue) — 100% secure, 100% private AI running locally.
System Grounding: Live System Time is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}. Never hallucinate historical training cutoff dates.
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

<Inter_Agent_Help_Protocol>
If you need assistance from Thinker or Nexus before finishing, embed:
===AGENT_HELP===
{{"call": "thinker", "reason": "Need verification of algorithm logic"}}
===AGENT_HELP_END===
</Inter_Agent_Help_Protocol>

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

    coder_llm = model_registry.get_model_for_role("coder", temperature=0.0)
    response = coder_llm.invoke([sys_prompt] + messages[-8:])
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

    final_content = raw
    if tool_results:
        final_content += "\n\n**[Meta-Hand Tool Results]**\n" + "\n".join(tool_results)

    observer.log_thought_process("Coder", "Execution Complete", "Forwarding to Thinker for verification.")

    return {
        "messages": [AIMessage(content=final_content)],
        "next_node": "Thinker",
        "agent_messages": [{"role": "coder", "content": final_content[:500], "tool_hint": ""}]
    }