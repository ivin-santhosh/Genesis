# Genesis Engineering Readiness (22 October 2026)

This repository is an **experimental local-first agent system**, not a certified production service. It must not be marketed as enterprise-production-ready solely because the source code exists or a demo prints a successful status.

## Features with public implementation evidence
- Three specialized roles: Nexus / Coder / Thinker, including a bounded collaborative loop.
- MCP tool registry and in-process agent-message state via LangGraph.
- Local Ollama-backed model routing.
- A window-based context compressor; it **drops** intermediate context rather than preserving every fact.
- An integration demonstration and deterministic security regression checks.

## Known gaps and requirements before a production deployment
1. **Security and permissions:** The high-risk agent-exposed tools are blocked by the dispatcher in the review branch. This does NOT make the MCP server safe by itself: tools are also exposed through the MCP server and need server-side authorization and process isolation. Dynamic Python execution has been disabled pending an OS-enforced sandbox.
2. **Recovery:** Task state is in memory; process-restart recovery and durable checkpoints are not implemented.
3. **Correctness and evaluation:** The Thinker uses an LLM self-assessment; it is not an independent oracle. A validated task benchmark, retrieval metrics, hallucination checks, and negative tests are needed.
4. **Async/runtime:** Real MCP client, Windows integration, model provisioning, retries, cancellation and timeout behavior need integration tests with supported dependencies and real Ollama.
5. **Deployment:** Provide versioned dependencies, least-privilege deployment, secret management, observability, logs/redaction, performance benchmarks, backups, rollback and alerts before external hosting.

## Tests
From the parent directory that contains the `Genesis/` checkout:
```shell
python -m compileall -q Genesis
PYTHONPATH=. python -m unittest discover -s Genesis/tests -v
```
PowerShell:
```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m unittest discover -s Genesis/tests -v
```
The CI workflow runs Python 3.11/3.12 syntax and deterministic security regression checks. These checks **do not exercise actual LLM requests** or prove full end-to-end functionality.

## Release gates
- [ ] All deterministic checks pass in CI
- [ ] Windows dependency installation and Ollama smoke test pass
- [ ] Actual MCP server can launch with least privileges and explicit tool allowlist
- [ ] Test suite covers routing, state transitions, tool failure, retries, cancellation, and memory boundaries
- [ ] Restart/resume and checkpoint consistency verified against crash injection
- [ ] Confidential data leakage and high-risk tool authorization tests pass
- [ ] Model and retrieval quality measured on labeled datasets
- [ ] Latency, throughput, saturation and load testing published with hardware configuration
- [ ] Threat model and operator documentation reviewed
- [ ] No secrets/private logs or real user information included in public repository

### Source evidence and claim policy
Local test assertions are not proof of a production SLA. A tool error returned as text is still a failure. Model-generated DONE is not evidence of independently verified correctness. Do not claim A2A wire-protocol compliance from an internal agent_messages list alone.
