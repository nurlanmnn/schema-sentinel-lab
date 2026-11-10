# Testbed checks

## Local setup - October 15, 2026

Tested on macOS with Python 3.13.7, Node.js 24.10.0, and .NET SDK 8.0.425.
The first run started with no project virtual environment, installed TypeScript
dependencies, or compiled output.

| Check | Result |
| --- | --- |
| `python3 run_local.py` | Dependencies installed; TypeScript and C# built; 11 unit tests and 4 round-trip cases passed |
| C# Release build | Zero warnings and errors |
| `python3 run_local.py start` | All three health checks passed; 4 messages passed from a second terminal |
| Ctrl+C | Services stopped and ports 8000-8002 were released |
| Missing .NET on PATH | Clear setup error before dependency installation |
| `git diff --check` | Passed |

The unit tests cover incorrect decoded values, missing services, changed returned
values, wrong service order, interpreter paths, missing tools, occupied ports,
process cleanup, and starting Python without reverse DNS. Round-trip cases cover normal strings, empty strings,
Unicode, and escaped text.

## Operating-system checks

The `Local testbed` GitHub Actions workflow runs the same first-run command on
Windows, macOS, and Ubuntu with Python 3.13, Node.js 22, and .NET 8.
Results appear in the PR checks.

The schema files, generated bindings, descriptor fixtures, and impact locator
source are unchanged by this PR.
