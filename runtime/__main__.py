"""Dependency-light demonstrable entrypoint: python -m Genesis.runtime"""
import argparse
import json
import sys
from pathlib import Path

from .engine import WorkflowEngine
from .state import CheckpointStore
from .tools import tool_names


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Project Genesis reliable local workflow demo")
    parser.add_argument("--db", default=str(Path.home() / ".genesis" / "state.sqlite3"))
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("tools")
    sub.add_parser("demo")
    plan = sub.add_parser("run")
    plan.add_argument("steps_file", help="JSON list of allowlisted tool operations")
    for command in ("status", "resume", "cancel"):
        p = sub.add_parser(command)
        p.add_argument("task_id")
    args = parser.parse_args(argv)
    if args.action == "tools":
        print(json.dumps({"available_tools": tool_names()}, indent=2))
        return 0
    store = CheckpointStore(args.db)
    try:
        engine = WorkflowEngine(store)
        if args.action == "demo":
            state = engine.plan([
                {"tool": "calculate", "args": {"expression": "(12+8)*3"}},
                {"tool": "utc_time"},
                {"tool": "system_status"},
            ])
            state = engine.execute(state["task_id"])
        elif args.action == "run":
            state = engine.plan(json.loads(Path(args.steps_file).read_text(encoding="utf-8")))
            state = engine.execute(state["task_id"])
        elif args.action == "status":
            state = store.load(args.task_id)
            if state is None:
                raise ValueError("Unknown task ID")
        elif args.action == "cancel":
            state = engine.cancel(args.task_id)
        else:
            state = engine.resume(args.task_id)
        print(json.dumps(state, indent=2, ensure_ascii=False))
        return 0 if state["status"] not in ("failed",) else 2
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
