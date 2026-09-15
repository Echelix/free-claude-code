"""Echelix background-server commands: fcc-start / fcc-stop / fcc-status."""

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from free_claude_code.cli import background


@pytest.fixture
def fcc_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    return tmp_path / ".fcc"


def test_pid_file_lives_under_managed_config_dir(fcc_home: Path) -> None:
    assert background.pid_file_path() == fcc_home / "fcc.pid"


def test_running_pid_returns_none_without_pid_file(fcc_home: Path) -> None:
    assert background.running_pid() is None


def test_running_pid_removes_stale_or_corrupt_pid_file(
    fcc_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fcc_home.mkdir()
    pid_file = fcc_home / "fcc.pid"

    pid_file.write_text("not-a-pid", encoding="utf-8")
    assert background.running_pid() is None
    assert not pid_file.exists()

    def dead(pid: int, sig: int) -> None:
        raise ProcessLookupError

    monkeypatch.setattr(background.os, "kill", dead)
    pid_file.write_text("4242", encoding="utf-8")
    assert background.running_pid() is None
    assert not pid_file.exists()


def test_running_pid_returns_live_pid(
    fcc_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fcc_home.mkdir()
    (fcc_home / "fcc.pid").write_text("4242\n", encoding="utf-8")
    checked: list[tuple[int, int]] = []
    monkeypatch.setattr(
        background.os, "kill", lambda pid, sig: checked.append((pid, sig))
    )

    assert background.running_pid() == 4242
    assert checked == [(4242, 0)]


def test_fcc_start_spawns_detached_server_and_records_pid(
    fcc_home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    launches: list[tuple[list[str], dict[str, object]]] = []

    def fake_popen(command: list[str], **kwargs: object) -> SimpleNamespace:
        launches.append((command, kwargs))
        return SimpleNamespace(pid=777)

    monkeypatch.setattr(background.subprocess, "Popen", fake_popen)

    background.fcc_start()

    assert (fcc_home / "fcc.pid").read_text(encoding="utf-8") == "777"
    ((command, kwargs),) = launches
    assert command[0] == sys.executable
    assert "free_claude_code.cli.entrypoints" in command[-1]
    assert kwargs["stdout"] is subprocess.DEVNULL
    assert kwargs["stderr"] is subprocess.DEVNULL
    if sys.platform == "win32":
        assert kwargs["creationflags"]
    else:
        assert kwargs["start_new_session"] is True
    out = capsys.readouterr().out
    assert "Proxy started (PID 777)" in out
    assert str(fcc_home / "logs" / "server.log") in out


def test_fcc_start_is_a_no_op_when_already_running(
    fcc_home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    fcc_home.mkdir()
    (fcc_home / "fcc.pid").write_text("4242", encoding="utf-8")
    monkeypatch.setattr(background.os, "kill", lambda pid, sig: None)

    def unexpected(*args: object, **kwargs: object) -> None:
        raise AssertionError("server must not be spawned twice")

    monkeypatch.setattr(background.subprocess, "Popen", unexpected)

    background.fcc_start()

    assert "already running (PID 4242)" in capsys.readouterr().out


def test_fcc_stop_signals_process_and_removes_pid_file(
    fcc_home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    fcc_home.mkdir()
    (fcc_home / "fcc.pid").write_text("4242", encoding="utf-8")
    signals: list[tuple[int, int]] = []
    monkeypatch.setattr(
        background.os, "kill", lambda pid, sig: signals.append((pid, sig))
    )

    background.fcc_stop()

    assert signals[0] == (4242, 0)
    assert signals[1][0] == 4242 and signals[1][1] != 0
    assert not (fcc_home / "fcc.pid").exists()
    assert "Proxy stopped (PID 4242)" in capsys.readouterr().out


def test_fcc_stop_and_status_report_not_running(
    fcc_home: Path, capsys: pytest.CaptureFixture
) -> None:
    background.fcc_stop()
    background.fcc_status()

    assert capsys.readouterr().out.count("Proxy is not running.") == 2


def test_fcc_status_reports_running_pid(
    fcc_home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    fcc_home.mkdir()
    (fcc_home / "fcc.pid").write_text(str(os.getpid()), encoding="utf-8")

    background.fcc_status()

    assert f"Proxy is running (PID {os.getpid()})" in capsys.readouterr().out
