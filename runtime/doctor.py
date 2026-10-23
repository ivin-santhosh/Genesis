"""Genesis installation diagnostics and consent-aware recovery.

Read-only by default. Safe local fixes require --repair-safe. Installing
packages, creating environments, or starting services requires a user choice.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .engine import WorkflowEngine
from .state import CheckpointStore

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = Path.home() / ".genesis"
OLLAMA_TAGS = "http://127.0.0.1:11434/api/tags"
# Never download or execute an arbitrary remote repair script.


@dataclass
class Check:
    name: str
    status: str
    detail: str
    fix: str = ""
    consequence: str = ""
    approval_action: str = ""


def _check_store() -> Check:
    try:
        with tempfile.TemporaryDirectory(prefix="genesis-health-") as tmp:
            store = CheckpointStore(Path(tmp) / "state.sqlite3")
            try:
                e = WorkflowEngine(store)
                s = e.plan([{"tool": "calculate", "args": {"expression": "(2+3)*4"}},
                            {"tool": "utc_time"}])
                result = e.execute(s["task_id"])
                if result["verdict"] != "PASS" or result["results"][0]["data"]["value"] != 20:
                    raise AssertionError("Unexpected deterministic result")
                store.connection.execute("PRAGMA quick_check")
                check = store.connection.execute("PRAGMA quick_check").fetchone()[0]
                if check != "ok":
                    raise RuntimeError("SQLite integrity check did not return ok")
            finally:
                store.close()
        return Check("workflow", "pass", "Bounded tools, checkpointing, and SQLite integration passed")
    except Exception as exc:
        return Check("workflow", "fail", f"{type(exc).__name__}: {str(exc)[:200]}",
                     "Verify writable temporary storage and supported Python installation")


def _check_state_dir(repair_safe: bool) -> Check:
    try:
        if not STATE_DIR.exists():
            if not repair_safe:
                return Check("state_directory", "warn", f"State directory missing: {STATE_DIR}",
                             "Run doctor --repair-safe to create an app-owned directory",
                             "Creates only an app-owned directory in your home folder")
            STATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not STATE_DIR.is_dir():
            raise RuntimeError("State location is not a directory")
        with tempfile.NamedTemporaryFile(dir=str(STATE_DIR), prefix=".health-", delete=True) as fp:
            fp.write(b"ok")
            fp.flush()
        return Check("state_directory", "pass", "Local application state directory is writable")
    except (PermissionError, OSError, RuntimeError) as exc:
        return Check("state_directory", "fail", f"Cannot write state: {exc}",
                     "Grant access to your user profile directory, or choose another writable HOME")


def _ollama_tags(timeout: float = 2.0) -> dict[str, Any]:
    with urllib.request.urlopen(OLLAMA_TAGS, timeout=timeout) as response:
        if response.status != 200:
            raise OSError(f"Ollama returned HTTP {response.status}")
        data = json.loads(response.read(1_000_000).decode("utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("models"), list):
            raise ValueError("Unexpected Ollama model-list response")
        return data


def _deep_llm_test(model: str) -> Check:
    body = json.dumps({
        "model": model, "stream": False,
        "messages": [
            {"role": "system", "content": "Return exactly the word GENESIS_OK."},
            {"role": "user", "content": "Connectivity smoke test"},
        ],
        "options": {"temperature": 0, "num_predict": 20},
    }).encode("utf-8")
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/chat",
                                     data=body, headers={"Content-Type": "application/json"},
                                     method="POST")
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read(250_000).decode("utf-8"))
        content = str(result.get("message", {}).get("content", "")).strip()
        if not content:
            raise ValueError("Ollama returned an empty model response")
        return Check("llm_inference", "pass", f"Local model {model} answered a real inference request")
    except Exception as exc:
        return Check("llm_inference", "fail", f"{type(exc).__name__}: {str(exc)[:200]}",
                     "Review local Ollama logs, model memory requirements, and VRAM usage")


def inspect(mode: str = "full", repair_safe: bool = False, deep: bool = False,
            model: str | None = None) -> dict[str, Any]:
    checks: list[Check] = []
    if sys.version_info < (3, 11):
        checks.append(Check("python", "fail", "Python 3.11 or newer is required",
                            "Install supported Python and recreate an isolated virtual environment"))
    else:
        checks.append(Check("python", "pass", f"{platform.python_implementation()} {platform.python_version()}"))
    checks.append(_check_state_dir(repair_safe))
    checks.append(_check_store())

    if mode == "full":
        for pkg in ("psutil", "mcp", "langgraph", "langchain_core", "langchain_ollama"):
            try:
                available = importlib.util.find_spec(pkg) is not None
            except (ImportError, ValueError, ModuleNotFoundError):
                available = False
            checks.append(Check(
                f"dependency_{pkg}", "pass" if available else "fail",
                f"{pkg} installed" if available else f"{pkg} missing",
                "" if available else "Install vetted dependencies inside an isolated virtual environment",
                "" if available else "Installs Python libraries from the configured package index",
                "" if available else "install_dependencies",
            ))

        exe = shutil.which("ollama")
        checks.append(Check(
            "ollama_cli", "pass" if exe else "fail",
            f"Ollama executable: {exe}" if exe else "Ollama executable not in PATH",
            "" if exe else "Install Ollama from its official publisher and add it to PATH",
            "" if exe else "Installs a local model-serving application",
        ))
        try:
            tags = _ollama_tags()
            checks.append(Check("ollama_api", "pass", "Ollama local service responded on 127.0.0.1:11434"))
            names = [str(m.get("name", "")) for m in tags["models"] if isinstance(m, dict)]
            if names:
                checks.append(Check("ollama_models", "pass", f"{len(names)} local model(s): {', '.join(names[:6])}"))
                selected = model or names[0]
                if deep:
                    checks.append(_deep_llm_test(selected))
                else:
                    checks.append(Check("llm_inference", "warn", "Live inference not tested (use --deep)",
                                        "Run doctor --deep to test actual local model inference",
                                        "Can load models into RAM/VRAM and consume CPU/GPU resources"))
            else:
                checks.append(Check("ollama_models", "fail", "No local Ollama models found",
                                    "Choose a compatible model, then run ollama pull MODEL",
                                    "Downloads model data and consumes disk space and bandwidth",
                                    "pull_model"))
        except (OSError, ValueError, urllib.error.URLError, TimeoutError) as exc:
            checks.append(Check("ollama_api", "fail", f"Cannot contact local Ollama: {str(exc)[:160]}",
                                "Start Ollama if installed, otherwise install it from the publisher",
                                "Starts a service listening locally and may reserve CPU/GPU resources",
                                "start_ollama" if exe else ""))
            checks.append(Check("ollama_models", "warn", "Cannot query installed models until server responds"))
            checks.append(Check("llm_inference", "warn", "Not tested: Ollama API unavailable"))

    failures = [c.name for c in checks if c.status == "fail"]
    warnings = [c.name for c in checks if c.status == "warn"]
    # Missing hardware tests or skip of real inference must never be treated as
    # evidence of full functionality.
    return {
        "mode": mode, "overall": "blocked" if failures else ("partial" if warnings else "passed"),
        "platform": platform.platform(), "python_executable": sys.executable,
        "checks": [asdict(c) for c in checks],
        "failed": failures, "not_verified": warnings,
        "qualification": ("Full local functional check passed" if not failures and not warnings and mode == "full" and deep
                          else "Not a full production certification"),
    }


def _guide(check: dict[str, Any]) -> None:
    print(f"  Problem: {check['detail']}")
    print(f"  Resolution: {check['fix'] or 'Inspect the diagnostic output and application logs.'}")
    if check.get("consequence"):
        print(f"  What changes: {check['consequence']}")
    print("  Alternative: Skip this optional capability; deterministic Genesis.runtime still works.")


def _explicit_action(action: str, *, model: str | None) -> str:
    if action == "start_ollama":
        exe = shutil.which("ollama")
        if not exe:
            return "Ollama is not installed. Use the official installer first."
        # Never try to elevate privileges or open firewall ports.
        log_path = STATE_DIR / "ollama-service.log"
        STATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
        with log_path.open("ab") as log:
            subprocess.Popen([exe, "serve"], stdin=subprocess.DEVNULL,
                             stdout=log, stderr=log, start_new_session=True)
        return f"Requested local Ollama service startup. Logs: {log_path}. Run doctor again."
    if action == "pull_model":
        if not model:
            return "Model not selected. Run doctor --model MODEL or follow the guided steps."
        exe = shutil.which("ollama")
        if not exe:
            return "Ollama executable not found"
        result = subprocess.run([exe, "pull", model], check=False, timeout=3600)
        return "Model download finished" if result.returncode == 0 else "Model download failed"
    if action == "install_dependencies":
        if sys.prefix == sys.base_prefix:
            return ("Refusing to install into global Python. First create and activate "
                    "a virtual environment (python -m venv .venv).")
        req = ROOT / "requirements-agent.txt"
        result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req)],
                                check=False, timeout=900)
        return "Dependencies installed" if result.returncode == 0 else "Dependency installation failed"
    return "No approved repair handler exists for this issue"


def interactive(report: dict[str, Any], model: str | None = None) -> None:
    choices = [c for c in report["checks"] if c["status"] != "pass" and c.get("fix")]
    for check in choices:
        print(f"\n[{check['status'].upper()}] {check['name']}: {check['detail']}")
        if check.get("approval_action"):
            print("  1. Ask permission and, if approved, execute the documented action")
        else:
            print("  1. Explanation only (no automatic repair available)")
        print("  2. Explain the repair steps, alternatives, and consequences")
        print("  3. Skip")
        try:
            selected = input("  Your choice [1/2/3]: ").strip()
        except EOFError:
            selected = "3"
        if selected == "1" and check.get("approval_action"):
            print(f"  Proposed: {check.get('fix')}")
            print(f"  Consequence: {check.get('consequence')}")
            try:
                permitted = input("  Explicitly authorize this action? [type YES]: ").strip()
            except EOFError:
                permitted = ""
            if permitted == "YES":
                try:
                    print("  " + _explicit_action(check["approval_action"], model=model))
                except (OSError, subprocess.TimeoutExpired) as exc:
                    print(f"  Action failed: {exc}")
            else:
                print("  Permission not granted; nothing changed.")
        elif selected == "2" or selected == "1":
            _guide(check)
    print("\nRechecked local status:")
    print(json.dumps(inspect(mode=report["mode"], model=model), indent=2))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Genesis health check and consent-aware repair")
    p.add_argument("--mode", choices=("core", "full"), default="full")
    p.add_argument("--json", action="store_true", help="Report without interactive prompts")
    p.add_argument("--repair-safe", action="store_true", help="Create local app state directory only")
    p.add_argument("--interactive", action="store_true", help="Offer approval or guided repair")
    p.add_argument("--deep", action="store_true", help="Run a real local LLM inference smoke test")
    p.add_argument("--model", help="Model name for smoke testing or explicitly approved download")
    args = p.parse_args(argv)
    report = inspect(mode=args.mode, repair_safe=args.repair_safe, deep=args.deep, model=args.model)
    print(json.dumps(report, indent=2))
    if args.interactive and not args.json:
        interactive(report, model=args.model)
    return 0 if report["overall"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
