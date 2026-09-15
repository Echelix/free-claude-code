"""Echelix background-server commands: ``fcc-start``, ``fcc-stop``, ``fcc-status``.

These wrap ``fcc-server`` so the proxy can run detached from the terminal and
survive across many ``claudex`` / ``fcc-claude`` sessions. State is a single
PID file under the managed FCC config directory (``~/.fcc/fcc.pid``).
"""

import contextlib
import os
import signal
import subprocess
import sys
from pathlib import Path

from free_claude_code.config.paths import config_dir_path, server_log_path

PID_FILENAME = "fcc.pid"
_SERVER_BOOTSTRAP = "from free_claude_code.cli.entrypoints import serve; serve()"


def pid_file_path() -> Path:
    """Return the background server PID file path."""

    return config_dir_path() / PID_FILENAME


def _process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)  # signal 0 = existence check only
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def running_pid() -> int | None:
    """Return the recorded PID when that process is still alive, else ``None``.

    A stale or unreadable PID file is removed as a side effect.
    """

    pid_file = pid_file_path()
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
    except FileNotFoundError:
        return None
    except OSError, ValueError:
        pid_file.unlink(missing_ok=True)
        return None
    if not _process_alive(pid):
        pid_file.unlink(missing_ok=True)
        return None
    return pid


def _server_command() -> list[str]:
    return [sys.executable, "-c", _SERVER_BOOTSTRAP]


def _spawn_detached_server() -> subprocess.Popen[bytes]:
    """Spawn ``fcc-server`` detached from this terminal session."""

    if sys.platform == "win32":
        return subprocess.Popen(
            _server_command(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    return subprocess.Popen(
        _server_command(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def fcc_start() -> None:
    """Start ``fcc-server`` detached in the background (registered as ``fcc-start``)."""

    pid = running_pid()
    if pid is not None:
        print(f"Proxy already running (PID {pid})")
        return

    pid_file = pid_file_path()
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    process = _spawn_detached_server()
    pid_file.write_text(str(process.pid), encoding="utf-8")
    print(f"Proxy started (PID {process.pid}) · logs → {server_log_path()}")


def fcc_stop() -> None:
    """Stop the background ``fcc-server`` (registered as ``fcc-stop``)."""

    pid = running_pid()
    if pid is None:
        print("Proxy is not running.")
        return

    stop_signal = signal.SIGTERM if sys.platform != "win32" else signal.SIGBREAK
    with contextlib.suppress(ProcessLookupError):
        os.kill(pid, stop_signal)
    pid_file_path().unlink(missing_ok=True)
    print(f"Proxy stopped (PID {pid})")


def fcc_status() -> None:
    """Print whether the background ``fcc-server`` is running (``fcc-status``)."""

    pid = running_pid()
    if pid is None:
        print("Proxy is not running.")
    else:
        print(f"Proxy is running (PID {pid})")
