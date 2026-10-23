# Genesis Doctor — machine-level installation and recovery

The **Doctor** runs a read-only health scan and generates a machine-readable JSON report. It checks Python version, writable state, a real SQLite workflow, optional dependencies, local Ollama executable/API, installed models, and optionally **real model inference**.

Run from the directory **containing** the `Genesis` folder:

```powershell
python -m Genesis.runtime.doctor --mode core --json
python -m Genesis.runtime.doctor --mode full --json
python -m Genesis.runtime.doctor --mode full --deep --interactive
```

For each issue, interactive mode offers:

**Option 1 — Permission path.** Shows the precise proposed repair and its consequence. Requires a second explicit `YES` before any privileged/operational repair action. The currently implemented actions are restricted to installing vetted packages into an *already activated* virtual environment, starting a local Ollama service, or downloading a user-selected model. It never elevates to administrator, edits firewall rules, or runs arbitrary scripts.

**Option 2 — Guided path.** Explains what is missing, the action to take, expected consequences, and the alternative of using the deterministic core without the optional component.

**Safe repair:** `--repair-safe` only creates `~/.genesis` if missing. Even this action is opt-in. **Read-only is the default.** Reports identify missing features and never label untested integrations as operational.

## Installation choices

- Create an isolated environment: `python -m venv .venv`; activate it on Windows with `\.venv\Scripts\Activate.ps1` (PowerShell execution policy may require an approved workaround).
- Install declared agent dependencies only after reviewing them: `python -m pip install -r Genesis/requirements-agent.txt`.
- Install Ollama from its official site and download only models you choose; these changes consume disk space and may run background services.
- `python -m Genesis.runtime.doctor --deep` sends a small local request to `127.0.0.1:11434`; a real model may load into VRAM and the test can take time.

## What cannot be self-repaired safely

Hardware faults, driver issues, insufficient VRAM, untrusted code, security permission decisions, corrupted user datasets and unsupported legacy code changes cannot be reliably fixed by an unattended AI program. The Doctor diagnoses these where possible and provides a guided alternative, but must never claim self-certified enterprise reliability. Legacy GUI, Telegram integration, and broad security tools are **outside** the current core/doctor test coverage.
