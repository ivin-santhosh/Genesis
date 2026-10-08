# Project Genesis

**Local-first multi-agent AI orchestration with MCP tool execution, A2A collaboration, and explicit verification.**

Project Genesis is an open-source experimental AI engineering system designed to coordinate specialized local agents while keeping tool execution observable and permission-aware. The current implementation uses LangGraph/LangChain-style orchestration, local Ollama-backed models, Model Context Protocol (MCP) tools, and an Agent-to-Agent (A2A) message channel.

## Why it exists

Most AI demos stop at a single model response. Genesis explores the harder systems problem: how multiple agents can plan, execute tools, verify each other, preserve state, and surface failures without silently swallowing errors.

The architecture separates responsibilities:

- **Nexus** - manager/planner that decomposes work.
- **Coder** - execution-oriented agent that can call registered MCP tools.
- **Thinker** - verifier/auditor that reviews outputs and issues DONE/CONTINUE verdicts.
- **Meta-Hand** - MCP tool registry and execution layer.
- **StateGraph** - routes agent state, progress callbacks, cancellation, and autonomous iterations.
- **Memory / A2A channel** - carries structured state and inter-agent messages between agents.

## Verified implementation highlights

The repository currently contains working code paths for:

- MCP server bootstrap and dynamic tool registration.
- A2A state passing between Nexus, Coder, and Thinker.
- Autonomous collaborative loops with bounded iteration count.
- Tool-call parsing and execution through a shared registry.
- Explicit error capture for missing or failed tools.
- Local model routing through Ollama.
- Permission/state fields in the shared Genesis state.
- Runtime progress callbacks and abort controls.
- A demonstration script for MCP + A2A integration.

## Architecture

~~~text
Human Request
    |
    v
Reflex / Routing Layer
    |
    v
Nexus (Plan)
    |
    v
Coder (Execute + MCP)
    |
    v
Thinker (Verify)
    |
    +---- DONE ----> Response
    |
    +-- CONTINUE --> next bounded A2A iteration

Shared across the loop:
- GenesisState
- agent_messages A2A channel
- Meta-Hand MCP registry
- local model registry
- observer / telemetry
~~~

## Repository map

~~~text
Genesis/
|-- agents/
|   |-- nexus.py
|   |-- coder.py
|   +-- thinker.py
|-- core/
|   |-- graph.py
|   |-- memory.py
|   |-- model_registry.py
|   +-- logger.py
|-- tools/
|   |-- mcp_tools.py
|   +-- meta_hand.py
|-- demo_a2a_mcp.py
|-- main.py
+-- LICENSE
~~~

## Quick verification

The repository includes a demonstration script that exercises A2A state passing, MCP tool registration/execution, and explicit error handling:

~~~bash
python demo_a2a_mcp.py
~~~

For the full local system, an Ollama installation and the project's Python dependencies are required. The current codebase is primarily Windows-oriented in several hardware/system integrations.

## Engineering principles demonstrated

- **Local-first execution:** designed around local model/runtime components.
- **Agent specialization:** planning, execution, and verification are separated.
- **Tool grounding:** agents can invoke deterministic tools rather than relying only on generated text.
- **Observable failure modes:** missing tools and tool exceptions are surfaced instead of silently ignored.
- **Permission-aware state:** execution state includes explicit permission fields.
- **Bounded autonomy:** autonomous collaboration is capped rather than running indefinitely.

## Current status

Genesis is an active engineering project, not a finished commercial product. The code demonstrates the architecture and core orchestration patterns; some platform-specific integrations and environment bootstrap logic are still evolving.

## License

Apache License 2.0.

## Project URL

https://github.com/ivin-santhosh/Genesis
