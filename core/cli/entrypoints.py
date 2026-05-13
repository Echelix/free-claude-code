"""CLI entry points for the installed package."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import uvicorn

from api.admin_urls import local_proxy_root_url
from api.app import GracefulLifespanApp, create_app
from config.settings import Settings, get_settings
from core.cli.process_registry import (
    kill_all_best_effort,
    kill_pid_tree_best_effort,
    register_pid,
    unregister_pid,
)

PROXY_PREFLIGHT_PATH = "/health"
PROXY_PREFLIGHT_TIMEOUT_SECONDS = 1.5
SERVER_GRACEFUL_SHUTDOWN_SECONDS = 5


def _load_env_template() -> str:
    """Load the canonical root env template from package resources or source."""
    import importlib.resources

    packaged = importlib.resources.files("core.cli").joinpath("env.example")
    if packaged.is_file():
        return packaged.read_text("utf-8")

    source_template = Path(__file__).resolve().parents[2] / ".env.example"
    if source_template.is_file():
        return source_template.read_text(encoding="utf-8")

    raise FileNotFoundError("Could not find bundled or source .env.example template.")


def serve() -> None:
    """Start the FastAPI server (registered as `fcc-server` / `free-claude-code` script)."""
    try:
        try:
            while True:
                settings = get_settings()
                if not _run_supervised_server(settings):
                    return
                get_settings.cache_clear()
        except KeyboardInterrupt:
            return
    finally:
        kill_all_best_effort()


def _run_supervised_server(settings: Settings) -> bool:
    """Run one uvicorn server instance; return whether admin requested restart."""

    restart_requested = False
    server_holder: dict[str, uvicorn.Server] = {}

    def request_restart() -> None:
        nonlocal restart_requested
        restart_requested = True
        if server := server_holder.get("server"):
            server.should_exit = True

    app = create_app(lifespan_enabled=False)
    app.state.admin_restart_callback = request_restart
    asgi_app = GracefulLifespanApp(app)
    config = uvicorn.Config(
        asgi_app,
        host=settings.host,
        port=settings.port,
        log_level="debug",
        timeout_graceful_shutdown=SERVER_GRACEFUL_SHUTDOWN_SECONDS,
    )
    server = uvicorn.Server(config)
    server_holder["server"] = server
    server.run()
    return restart_requested


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
    print("Edit it to set your API keys and model preferences, then run: fcc-server")


def _claude_child_env(
    settings: Settings, base_env: Mapping[str, str]
) -> dict[str, str]:
    """Return a Claude Code environment that targets this proxy."""

    env = {
        key: value
        for key, value in base_env.items()
        if not key.startswith("ANTHROPIC_")
    }
    env["ANTHROPIC_BASE_URL"] = local_proxy_root_url(settings)
    env["CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY"] = "1"
    if token := settings.anthropic_auth_token.strip():
        env["ANTHROPIC_AUTH_TOKEN"] = token
    return env


def _preflight_proxy(proxy_root_url: str) -> str | None:
    """Return an error message when the local proxy health check is unreachable."""

    url = f"{proxy_root_url.rstrip('/')}{PROXY_PREFLIGHT_PATH}"
    request = Request(url, method="GET")
    try:
        with urlopen(request, timeout=PROXY_PREFLIGHT_TIMEOUT_SECONDS) as response:
            status_code = response.getcode()
    except HTTPError as exc:
        return f"returned HTTP {exc.code}"
    except URLError as exc:
        return str(exc.reason)
    except OSError as exc:
        return str(exc)

    if not 200 <= status_code < 300:
        return f"returned HTTP {status_code}"
    return None


def launch_claude(argv: Sequence[str] | None = None) -> None:
    """Launch Claude Code with Free Claude Code proxy environment variables."""

    settings = get_settings()
    proxy_root_url = local_proxy_root_url(settings)
    if error := _preflight_proxy(proxy_root_url):
        print(
            f"Free Claude Code proxy is not reachable at {proxy_root_url}: {error}",
            file=sys.stderr,
        )
        print("Start it in another terminal with: fcc-server", file=sys.stderr)
        raise SystemExit(1)

    args = list(sys.argv[1:] if argv is None else argv)
    claude_command = shutil.which(settings.claude_cli_bin)
    if claude_command is None:
        print(
            f"Could not find Claude Code command: {settings.claude_cli_bin}",
            file=sys.stderr,
        )
        print(
            "Install Claude Code with: npm install -g @anthropic-ai/claude-code",
            file=sys.stderr,
        )
        raise SystemExit(127)

    command = [claude_command, *args]
    env = _claude_child_env(settings, os.environ)
    process: subprocess.Popen[bytes] | None = None
    try:
        process = subprocess.Popen(command, env=env)
        if process.pid:
            register_pid(process.pid)
        return_code = process.wait()
    except FileNotFoundError:
        print(
            f"Could not find Claude Code command: {settings.claude_cli_bin}",
            file=sys.stderr,
        )
        print(
            "Install Claude Code with: npm install -g @anthropic-ai/claude-code",
            file=sys.stderr,
        )
        raise SystemExit(127) from None
    except KeyboardInterrupt:
        if process is not None and process.pid:
            kill_pid_tree_best_effort(process.pid)
            process.wait()
        raise
    finally:
        if process is not None and process.pid:
            unregister_pid(process.pid)

    raise SystemExit(return_code)


def claudex() -> None:
    """Launch Claude CLI pointed at the local proxy (registered as `claudex`).

    Reads ANTHROPIC_AUTH_TOKEN and port from settings (.env), then exec-replaces
    itself with `claude` on Unix or spawns it on Windows, preserving the caller's
    working directory and forwarding any extra arguments.
    """
    # Pin the .env lookup to the project root so settings loads correctly
    # regardless of what directory the user invokes claudex from.
    if "FCC_ENV_FILE" not in os.environ:
        project_env = Path(__file__).resolve().parents[2] / ".env"
        if project_env.is_file():
            os.environ["FCC_ENV_FILE"] = str(project_env)

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
    pid = _running_pid()
    if pid is not None:
        print(f"Proxy already running (PID {pid})")
        return

    server_bin = Path(sys.executable).parent / (
        "free-claude-code.exe" if sys.platform == "win32" else "free-claude-code"
    )
    root = _project_root()

    kwargs: dict = {
        "cwd": str(root),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
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
    import signal

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
