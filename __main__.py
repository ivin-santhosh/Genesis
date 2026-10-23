"""python -m Genesis starts the safe, first-run-capable launcher."""
from .runtime.launcher import main

if __name__ == "__main__":
    raise SystemExit(main())
