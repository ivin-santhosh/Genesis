"""First-run interactive Genesis launcher. Uses Python standard library by default."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from .doctor import _ollama_tags
from .engine import WorkflowEngine
from .state import CheckpointStore
from .tools import execute_tool, tool_names
from .chat import OllamaClient, LocalAssistant

HELP = """Commands:
  /help              Show commands
  /tools             List safe local tools
  /calc EXPR         Run deterministic arithmetic
  /time              Current UTC time
  /system            Local system summary
  /demo              Execute checkpointed three-step workflow
  /doctor            Diagnose optional AI capabilities
  /setup             Consent-aware AI setup guidance
  /models            Show installed Ollama models
  /model NAME        Use an installed local model
  /reset             Clear local conversation history
  /quit              Exit
Other input goes to local Ollama when configured.
"""


def installed_models() -> list[str]:
    try:
        data = _ollama_tags()
        return [str(m.get("name")) for m in data["models"]
                if isinstance(m, dict) and m.get("name")]
    except (OSError, ValueError, TimeoutError):
        return []


def launch(model: str | None = None, state_file: str | None = None,
           input_fn=input, print_fn=print) -> int:
    print_fn("Genesis | Local-first interactive assistant")
    print_fn("No external setup required for /calc, /time, /system and /demo.")
    print_fn(HELP)
    store = CheckpointStore(state_file or Path.home() / ".genesis" / "state.sqlite3")
    try:
        models = installed_models()
        selected = model if model in models else (models[0] if models else None)
        assistant = LocalAssistant(OllamaClient(selected)) if selected else None
        if selected:
            print_fn(f"Local AI ready: {selected}")
        else:
            print_fn("Local AI not configured. Offline commands are ready; use /setup for AI activation.")
        while True:
            try:
                raw = input_fn("genesis> ").strip()
            except (EOFError, KeyboardInterrupt):
                print_fn("Goodbye.")
                return 0
            if not raw:
                continue
            cmd, _, arg = raw.partition(" ")
            cmd = cmd.lower()
            if cmd in ("/quit", "/exit"):
                return 0
            if cmd == "/help":
                print_fn(HELP)
            elif cmd == "/tools":
                print_fn(", ".join(tool_names()))
            elif cmd in ("/calc", "/time", "/system"):
                name = {"/calc": "calculate", "/time": "utc_time",
                        "/system": "system_status"}[cmd]
                args = {"expression": arg} if cmd == "/calc" else {}
                print_fn(json.dumps(execute_tool(name, args), indent=2))
            elif cmd == "/models":
                models = installed_models()
                print_fn("Local models: " + (", ".join(models) if models else "none detected"))
            elif cmd == "/model":
                models = installed_models()
                if arg not in models:
                    print_fn("Model is not installed. Use /setup for guidance.")
                else:
                    selected = arg
                    assistant = LocalAssistant(OllamaClient(selected))
                    print_fn(f"Model changed: {selected}; conversation reset")
            elif cmd == "/reset":
                if assistant:
                    assistant.reset()
                print_fn("In-memory conversation reset.")
            elif cmd == "/demo":
                steps = [{"tool": "calculate", "args": {"expression": "(5+7)*2"}},
                         {"tool": "utc_time"}, {"tool": "system_status"}]
                state = WorkflowEngine(store).plan(steps)
                result = WorkflowEngine(store).execute(state["task_id"])
                print_fn(json.dumps({"task_id": result["task_id"],
                                     "status": result["status"],
                                     "verdict": result["verdict"]}, indent=2))
            elif cmd in ("/doctor", "/setup"):
                from .doctor import inspect, interactive
                report = inspect(mode="full", deep=False)
                print_fn(json.dumps({"overall": report["overall"],
                                     "failed": report["failed"],
                                     "not_verified": report["not_verified"]}, indent=2))
                if cmd == "/setup":
                    interactive(report)
                    models = installed_models()
                    if models:
                        selected = models[0]
                        assistant = LocalAssistant(OllamaClient(selected))
            elif cmd.startswith("/"):
                print_fn("Unknown command. Type /help.")
            elif assistant:
                try:
                    print_fn(assistant.ask(raw))
                except (OSError, RuntimeError, ValueError, TimeoutError) as exc:
                    print_fn(f"Local model error: {type(exc).__name__}: {str(exc)[:250]}. Try /doctor.")
            else:
                print_fn("An AI model is not available. Use /setup for two repair choices, "
                         "or try /help for available offline functions.")
    finally:
        store.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Launch Genesis interactive assistant")
    parser.add_argument("--model", default=None, help="Already installed local Ollama model")
    parser.add_argument("--db", default=None, help="SQLite task database")
    args = parser.parse_args(argv)
    return launch(model=args.model, state_file=args.db)


if __name__ == "__main__":
    raise SystemExit(main())
