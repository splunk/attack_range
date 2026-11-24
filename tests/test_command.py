import os
import select
import threading
import time
from pathlib import Path

import pytest
from rich.console import Console

from attack_range.application.operator import HangChoice
from attack_range.application.provisioner import NullProvisionLog, ProvisionerError
from attack_range_infrastructure.command import CommandIdle, stream_command
from attack_range_infrastructure.guests import AnsibleGuestProvisioner
from cli.operator import CliOperator


def _script(path: Path, body: str) -> Path:
    path.write_text(body)
    path.chmod(0o755)
    return path


def test_silence_can_keep_waiting(tmp_path: Path) -> None:
    script = _script(tmp_path / "slow", "#!/bin/sh\nsleep 0.6\necho finished\n")
    asked: list[str] = []

    result = stream_command(
        [str(script)],
        tmp_path,
        NullProvisionLog(),
        idle_timeout=0.2,
        on_idle=lambda last, output: asked.append(last) or "wait",
    )

    assert result.returncode == 0
    assert "finished" in result.stdout
    assert asked


def test_silence_can_retry(tmp_path: Path) -> None:
    script = _script(tmp_path / "stuck", "#!/bin/sh\nsleep 30\n")
    started = time.monotonic()

    with pytest.raises(CommandIdle):
        stream_command(
            [str(script)],
            tmp_path,
            NullProvisionLog(),
            idle_timeout=0.2,
            on_idle=lambda last, output: "retry",
        )

    assert time.monotonic() - started < 5


def test_silence_can_abort(tmp_path: Path) -> None:
    script = _script(tmp_path / "stuck", "#!/bin/sh\nsleep 30\n")

    with pytest.raises(ProvisionerError, match="hung command"):
        stream_command(
            [str(script)],
            tmp_path,
            NullProvisionLog(),
            idle_timeout=0.2,
            on_idle=lambda last, output: "abort",
        )


def test_a_hung_command_is_run_again(home, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def fake_stream(command, directory, log, environment=None, idle_timeout=None, on_idle=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise CommandIdle("stuck")
        log.line("ok")
        return __import__("subprocess").CompletedProcess(command, 0, "ok\n", "")

    monkeypatch.setattr("attack_range_infrastructure.guests.stream_command", fake_stream)

    result = AnsibleGuestProvisioner(home)._run(tmp_path, ["ansible-playbook"], "ansible-playbook servers")

    assert calls["n"] == 2
    assert result.returncode == 0


def test_a_failed_gateway_play_is_tried_three_times(
    home, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    count = tmp_path / "runs"
    _script(
        tmp_path / "ansible-playbook",
        "#!/bin/sh\n"
        f"n=0; [ -f {count} ] && n=$(cat {count}); n=$((n + 1)); echo $n > {count}\n"
        'echo "unreachable=0 failed=1"\n'
        "exit 2\n",
    )
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setattr("attack_range_infrastructure.guests.time.sleep", lambda seconds: None)
    log = _Log()

    with pytest.raises(ProvisionerError, match="could not provision the wireguard gateway"):
        AnsibleGuestProvisioner(home, log=log)._ansible(tmp_path, "deploy", retry=False)

    assert count.read_text().strip() == "3"
    assert "ansible-playbook wireguard deploy failed, retrying (2/3)" in log.lines
    assert "ansible-playbook wireguard deploy failed, retrying (3/3)" in log.lines


def test_a_gateway_play_stops_retrying_when_it_succeeds(
    home, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    count = tmp_path / "runs"
    _script(
        tmp_path / "ansible-playbook",
        "#!/bin/sh\n"
        f"n=0; [ -f {count} ] && n=$(cat {count}); n=$((n + 1)); echo $n > {count}\n"
        '[ "$n" -ge 2 ] && exit 0\n'
        "exit 2\n",
    )
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setattr("attack_range_infrastructure.guests.time.sleep", lambda seconds: None)

    AnsibleGuestProvisioner(home)._ansible(tmp_path, "deploy", retry=False)

    assert count.read_text().strip() == "2"


def test_an_unreachable_gateway_keeps_waiting_for_ssh(
    home, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    count = tmp_path / "runs"
    _script(
        tmp_path / "ansible-playbook",
        "#!/bin/sh\n"
        f"n=0; [ -f {count} ] && n=$(cat {count}); n=$((n + 1)); echo $n > {count}\n"
        '[ "$n" -ge 4 ] && exit 0\n'
        'echo "Failed to connect to the host via ssh"\n'
        "exit 3\n",
    )
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setattr("attack_range_infrastructure.guests.time.sleep", lambda seconds: None)
    log = _Log()

    AnsibleGuestProvisioner(home, log=log)._ansible(tmp_path, "deploy", retry=True)

    assert count.read_text().strip() == "4"
    assert log.lines.count("wireguard gateway is not reachable yet, retrying") == 3
    assert not any("failed, retrying" in line for line in log.lines)


def test_unattended_hang_aborts(home, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_stream(command, directory, log, environment=None, idle_timeout=None, on_idle=None):
        assert on_idle is not None
        assert on_idle("last task", 0) == "abort"
        raise ProvisionerError("stopped a hung command after 300s with no output")

    monkeypatch.setattr("attack_range_infrastructure.guests.stream_command", fake_stream)

    with pytest.raises(ProvisionerError, match="hung command"):
        AnsibleGuestProvisioner(home)._run(tmp_path, ["ansible-playbook"], "ansible-playbook servers")


def test_output_during_the_prompt_continues_the_same_process(tmp_path: Path) -> None:
    script = _script(tmp_path / "slow", "#!/bin/sh\nsleep 0.4\necho resumed\n")

    def on_idle(last: str, output: int) -> str:
        select.select([output], [], [], 2)
        return "continue"

    result = stream_command(
        [str(script)],
        tmp_path,
        NullProvisionLog(),
        idle_timeout=0.1,
        on_idle=on_idle,
    )

    assert result.returncode == 0
    assert "resumed" in result.stdout


def test_prompt_closes_when_the_command_prints_before_an_answer() -> None:
    output_read, output_write = os.pipe()
    stdin_read, stdin_write = os.pipe()
    try:
        printed: list[str] = []

        def resume() -> None:
            time.sleep(0.2)
            os.write(output_write, b"TASK ok\n")

        writer = threading.Thread(target=resume)
        writer.start()
        operator = CliOperator()
        operator._out = Console(file=_Capture(printed), force_terminal=True, width=80)
        choice = operator._choose(
            "ansible-playbook servers",
            300,
            "install splunk binary from tarball",
            os.fdopen(stdin_read, "r"),
            output_read,
        )
        writer.join()

        assert choice is HangChoice.CONTINUE
        rendered = "".join(printed)
        assert "\033[1A" in rendered
        text = " ".join(rendered.split())
        assert "no output for 300s" in text
        assert "r and Enter to retry" in text
        assert "w and Enter to keep waiting" in text
        assert "a and Enter to abort" in text
        assert "\033[1A" in rendered
    finally:
        for fd in (output_read, output_write, stdin_write):
            os.close(fd)


class _Log:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def line(self, text: str) -> None:
        self.lines.append(text)


class _Capture:
    """Collects what the prompt writes, including the erase sequence."""

    def __init__(self, parts: list[str]) -> None:
        self.parts = parts

    def write(self, text: str) -> int:
        self.parts.append(text)
        return len(text)

    def flush(self) -> None:
        return
