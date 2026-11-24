"""Run a command and send each line of its output to the provision log."""

import os
import select
import signal
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional

from attack_range.application.provisioner import ProvisionLog, ProvisionerError

IdleDecision = Callable[[str, int], str]
"""Called with the last output line and the command stdout.

Returns ``wait``, ``retry``, ``abort``, ``continue``, or ``later``. ``continue``
means the command printed again while the prompt was up, so the same process
keeps running. ``later`` means another prompt is already showing: keep reading
this process and ask again without resetting the idle timer.
"""


class CommandIdle(Exception):
    """The command was stopped because it produced no output and the operator chose to retry."""

    def __init__(self, output: str) -> None:
        super().__init__(output)
        self.output = output


def stream_command(
    command: list[str],
    directory: Path,
    log: ProvisionLog,
    environment: Optional[dict[str, str]] = None,
    idle_timeout: Optional[float] = None,
    on_idle: Optional[IdleDecision] = None,
) -> subprocess.CompletedProcess[str]:
    """Merge stdout and stderr and show each line as it arrives.

    When `idle_timeout` is set and nothing arrives for that many seconds, `on_idle`
    decides whether to keep waiting, stop and retry, or abort. The process keeps
    running while that decision is made. It is stopped on retry or abort. `continue`
    means output resumed first: the prompt is already gone and the same process is read again.
    """
    lines: list[str] = []
    pending = ""
    with subprocess.Popen(
        command,
        cwd=directory,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=True,
    ) as process:
        assert process.stdout is not None
        os.set_blocking(process.stdout.fileno(), False)
        last_output = time.monotonic()
        try:
            while True:
                timeout = 1.0
                if idle_timeout is not None:
                    timeout = min(1.0, max(0.0, idle_timeout - (time.monotonic() - last_output)))
                ready, _, _ = select.select([process.stdout], [], [], timeout)
                if ready:
                    chunk = _read(process.stdout)
                    if chunk:
                        last_output = time.monotonic()
                        pending += chunk
                        while "\n" in pending:
                            line, pending = pending.split("\n", 1)
                            lines.append(line + "\n")
                            log.line(line)
                        continue
                    if process.poll() is not None:
                        break
                elif process.poll() is not None:
                    break
                elif idle_timeout is not None and time.monotonic() - last_output >= idle_timeout:
                    decision = (
                        on_idle(_last_line(lines, pending), process.stdout.fileno())
                        if on_idle is not None
                        else "abort"
                    )
                    if decision == "continue":
                        pending_output, _, _ = select.select([process.stdout], [], [], 0)
                        if not pending_output:
                            last_output = time.monotonic()
                        continue
                    if decision == "later":
                        select.select([process.stdout], [], [], 0.2)
                        continue
                    if decision == "wait":
                        last_output = time.monotonic()
                        continue
                    _stop(process)
                    output = "".join(lines)
                    if decision == "retry":
                        raise CommandIdle(output)
                    raise ProvisionerError(
                        f"stopped a hung command after {int(idle_timeout)}s with no output"
                    )
        finally:
            if process.poll() is None:
                _stop(process)
        if pending:
            lines.append(pending)
            log.line(pending.rstrip("\n"))
        returncode = process.wait()
    return subprocess.CompletedProcess(command, returncode, "".join(lines), "")


def _read(stream: object) -> str:
    try:
        return stream.read() or ""  # type: ignore[attr-defined]
    except BlockingIOError:
        return ""


def _last_line(lines: list[str], pending: str) -> str:
    if pending.strip():
        return pending.strip()
    for line in reversed(lines):
        if line.strip():
            return line.strip()
    return ""


def _stop(process: subprocess.Popen[str]) -> None:
    """Stop the command and the children it started."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        process.wait()
