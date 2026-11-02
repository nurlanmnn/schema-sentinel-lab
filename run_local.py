"""Set up and run the testbed on Windows, macOS, or Linux."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def venv_python(root=ROOT, platform=sys.platform):
    folder = "Scripts" if platform == "win32" else "bin"
    filename = "python.exe" if platform == "win32" else "python"
    return root / ".venv" / folder / filename


def run(command):
    print("\n> " + subprocess.list2cmdline([str(part) for part in command]), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def check_tools():
    if sys.version_info < (3, 10):
        raise RuntimeError("Python 3.10 or newer is required.")
    tools = {name: shutil.which(name) for name in ("node", "npm", "dotnet")}
    missing = [name for name, path in tools.items() if path is None]
    if missing:
        raise RuntimeError(
            "Missing from PATH: " + ", ".join(missing)
            + ". Install Node.js 22+ (includes npm) and the .NET 8 SDK, then reopen your terminal."
        )
    node_version = subprocess.check_output([tools["node"], "--version"], text=True).strip()
    if int(node_version.lstrip("v").split(".")[0]) < 22:
        raise RuntimeError(f"Node.js 22 or newer is required; found {node_version}.")
    sdks = subprocess.check_output([tools["dotnet"], "--list-sdks"], text=True)
    if not any(line.startswith("8.") for line in sdks.splitlines()):
        raise RuntimeError("Install the .NET 8 SDK. The .NET runtime alone is not enough.")
    print(f"Python {sys.version.split()[0]}, Node.js {node_version}, and .NET 8 SDK found.", flush=True)
    return tools


def setup(tools):
    python = venv_python()
    if not python.exists():
        run([sys.executable, "-m", "venv", str(ROOT / ".venv")])
    run([str(python), "-m", "pip", "install", "-r", "runtimes/python/requirements.txt"])
    run([tools["npm"], "ci", "--prefix", "runtimes/typescript"])
    run([tools["dotnet"], "restore", "runtimes/csharp/CsharpApp.csproj"])


def build(tools):
    if not venv_python().exists():
        raise RuntimeError("Setup is missing. Run this script without arguments first.")
    run([tools["npm"], "run", "build", "--prefix", "runtimes/typescript"])
    run([tools["dotnet"], "build", "runtimes/csharp/CsharpApp.csproj", "--configuration", "Release"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", default="all", choices=("all", "setup", "test", "start", "pubsub"),
                        help="all: setup and test (default); setup: install dependencies; test: build and test; start: build and keep services running; pubsub: build and check fan-out")
    parser.add_argument("--output", type=Path, help="new pubsub evidence directory (required for pubsub)")
    args = parser.parse_args()
    if args.command == "pubsub" and args.output is None:
        parser.error("pubsub requires --output NEW-DIRECTORY")
    if args.command != "pubsub" and args.output is not None:
        parser.error("--output is supported only for pubsub")
    try:
        tools = check_tools()
        if args.command in ("all", "setup"):
            setup(tools)
        if args.command == "setup":
            print("\nSetup complete. Run this script with 'test' to run the checks.")
            return 0
        build(tools)
        python = str(venv_python())
        if args.command != "start":
            run([python, "-m", "unittest", "discover", "-s", "testbed/tests", "-p", "test_*.py", "-v"])
        if args.command == "pubsub":
            run([python, "-m", "testbed.pubsub.run", "--output", args.output])
            return 0
        command = [python, "testbed/scripts/run-local.py"]
        if args.command == "start":
            command.append("--serve")
        run(command)
        return 0
    except RuntimeError as error:
        print(f"\nError: {error}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        print(f"\nCommand failed (exit {error.returncode}). See the output above.", file=sys.stderr)
        return error.returncode
    except OSError as error:
        print(f"\nError: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nStopped.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
