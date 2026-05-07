"""CLI entry points for the installed package."""

from __future__ import annotations

from pathlib import Path


def _load_env_template() -> str:
    """Load the canonical root env template from package resources or source."""
    import importlib.resources

    packaged = importlib.resources.files("core.cli").joinpath("env.example")
    if packaged.is_file():
        return packaged.read_text("utf-8")

    source_template = Path(__file__).resolve().parents[1] / ".env.example"
    if source_template.is_file():
        return source_template.read_text(encoding="utf-8")

    raise FileNotFoundError("Could not find bundled or source .env.example template.")


def serve() -> None:
    """Start the FastAPI server (registered as `free-claude-code` script)."""
    import uvicorn

    from core.cli.process_registry import kill_all_best_effort
    from config.settings import get_settings

    settings = get_settings()
    try:
        uvicorn.run(
            "api.app:create_app",
            factory=True,
            host=settings.host,
            port=settings.port,
            log_level="debug",
            timeout_graceful_shutdown=5,
        )
    finally:
        kill_all_best_effort()


def claudex() -> None:
    """Launch Claude CLI pointed at the local proxy (registered as `claudex`).

    Reads ANTHROPIC_AUTH_TOKEN and port from settings (.env), then exec-replaces
    itself with `claude` on Unix or spawns it on Windows, preserving the caller's
    working directory and forwarding any extra arguments.
    """
    import os
    import subprocess
    import sys

    # Pin the .env lookup to the project root so settings loads correctly
    # regardless of what directory the user invokes claudex from.
    if "FCC_ENV_FILE" not in os.environ:
        project_env = Path(__file__).resolve().parents[2] / ".env"
        if project_env.is_file():
            os.environ["FCC_ENV_FILE"] = str(project_env)

    from config.settings import get_settings

    settings = get_settings()

    env = os.environ.copy()
    env["ANTHROPIC_AUTH_TOKEN"] = settings.anthropic_auth_token
    env["ANTHROPIC_BASE_URL"] = f"http://localhost:{settings.port}"

    args = ["claude", *sys.argv[1:]]

    if sys.platform == "win32":
        result = subprocess.run(args, env=env)
        sys.exit(result.returncode)
    else:
        os.execvpe("claude", args, env)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _pid_file() -> Path:
    return _project_root() / ".fcc.pid"


def _running_pid() -> int | None:
    """Return the PID from the pid file if the process is still alive, else None."""
    import os

    pid_file = _pid_file()
    if not pid_file.exists():
        return None
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)  # signal 0 = existence check only
        return pid
    except ValueError, ProcessLookupError, PermissionError:
        pid_file.unlink(missing_ok=True)
        return None


def fcc_start() -> None:
    """Start the proxy server in the background (registered as `fcc-start`).

    The process is detached from the terminal so it keeps running after the
    shell exits. Logs go to server.log in the project directory as usual.
    Prints the PID and exits immediately.
    """
    import subprocess
    import sys

    pid = _running_pid()
    if pid is not None:
        print(f"Proxy already running (PID {pid})")
        return

    server_bin = Path(sys.executable).parent / (
        "free-claude-code.exe" if sys.platform == "win32" else "free-claude-code"
    )
    root = _project_root()

    kwargs: dict = dict(
        cwd=str(root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if sys.platform == "win32":
        kwargs["creationflags"] = (
            subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        kwargs["start_new_session"] = True  # detach from terminal session

    proc = subprocess.Popen([str(server_bin)], **kwargs)
    _pid_file().write_text(str(proc.pid))
    print(f"Proxy started (PID {proc.pid}) · logs → {root / 'server.log'}")


def fcc_stop() -> None:
    """Stop the background proxy server (registered as `fcc-stop`)."""
    import os
    import signal
    import sys

    pid = _running_pid()
    if pid is None:
        print("Proxy is not running.")
        return

    os.kill(pid, signal.SIGTERM if sys.platform != "win32" else signal.SIGBREAK)
    _pid_file().unlink(missing_ok=True)
    print(f"Proxy stopped (PID {pid})")


def fcc_status() -> None:
    """Print whether the proxy server is running (registered as `fcc-status`)."""
    pid = _running_pid()
    if pid is None:
        print("Proxy is not running.")
    else:
        print(f"Proxy is running (PID {pid})")


def init() -> None:
    """Scaffold config at ~/.config/free-claude-code/.env (registered as `fcc-init`)."""
    config_dir = Path.home() / ".config" / "free-claude-code"
    env_file = config_dir / ".env"

    if env_file.exists():
        print(f"Config already exists at {env_file}")
        print("Delete it first if you want to reset to defaults.")
        return

    config_dir.mkdir(parents=True, exist_ok=True)
    template = _load_env_template()
    env_file.write_text(template, encoding="utf-8")
    print(f"Config created at {env_file}")
    print(
        "Edit it to set your API keys and model preferences, then run: free-claude-code"
    )
