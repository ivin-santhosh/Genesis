# Genesis: deterministic local workflow runtime

The `Genesis.runtime` package is a **working baseline for auditable tool orchestration**, separate from the legacy experimental LLM/UI implementation. It provides:

- A fixed allowlist of read-only tools, including arithmetic, UTC time, system status, and optional `psutil`-based process/network summaries.
- Plan → execute → deterministic verification (PASS or FAIL).
- SQLite checkpoints, replay protection after uncertain in-flight tool operations, cancellation and bounded execution.
- A zero-LLM demo that is suitable for a reproducible engineering walkthrough.

## Run

From the **parent folder** containing the `Genesis` checkout:

```powershell
python -m Genesis.runtime --db .genesis-state.sqlite3 demo
python -m Genesis.runtime --db .genesis-state.sqlite3 tools
```

To submit your own planned operations, save the following JSON as `steps.json`:

```json
[{"tool":"calculate","args":{"expression":"(10+2)/3"}},{"tool":"utc_time"}]
```

```powershell
python -m Genesis.runtime --db .genesis-state.sqlite3 run steps.json
```

Other commands: `status TASK_ID`, `resume TASK_ID`, and `cancel TASK_ID`.

## Tests

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m unittest discover -s Genesis/tests -v
```

Optional additional diagnostics: `python -m pip install psutil`. The demo does not require Ollama or FastMCP.

## What this does *not* prove

This is not a replacement for the full Genesis multi-agent system, a model benchmark, or an enterprise production release. The original Genesis `main.py` still contains runtime bootstrap and Windows-specific integration concerns. The standalone runtime verifies safe deterministic tool orchestration and recovery behavior; agent reasoning and true end-to-end MCP connections still require separate validation.

**Security:** Do not grant arbitrary shell, Python execution or write access to untrusted AI model outputs. Treat every external tool output as untrusted. For mutating tools, implement authenticated authorization, idempotency and a durable work queue before enabling execution.
