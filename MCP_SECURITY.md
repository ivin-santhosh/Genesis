# Default-deny MCP server exposure

The public STDIO MCP server now registers only these explicitly reviewed utilities:

- Arithmetic: add_float, subtract_float, multiply_float, divide_float, add_int, subtract_int, multiply_int, divide_int
- Date/time: get_datetime
- Defensive classification utilities: severity_score, mitre_guess

All other functions may remain in the source for compatibility but are **not registered as MCP tools** through `@mcp.tool()`. This includes `run_cmd`, `run_powershell`, firewall mutations, antivirus operations, custom Python execution, arbitrary workflow dispatch and report uploads.

This is a deliberate breaking security change. NetProbe-style telemetry and broad diagnostic access will NOT work through this default server until each operation is separately audited, protected, and intentionally allowed.

The client-side MetaHand gateway alone was insufficient because external MCP clients can connect directly. Deny-by-default registration now makes the public server surface narrower. **It does not make running the entire Python module risk-free**: import-time side effects, sensitive data in tracked artifacts, third-party dependencies and local code execution outside the public MCP protocol remain separate concerns.

The present `mcp.run()` invocation precedes additional function definitions in the file; definitions after it are not made available through the normal main execution path. Further refactoring should move startup to the end of the module after eliminating unrelated side effects and unused legacy tools.

## Test scope

`python -m unittest discover -s Genesis/tests -v` verifies the source allowlist, excluded dangerous names and its decorator gate, in addition to earlier security regressions.

Tests are **not** a live end-to-end MCP handshake, Windows security integration test, or penetration test. Run real server integration tests in a disposable least-privilege environment before re-enabling any sensitive tools.
