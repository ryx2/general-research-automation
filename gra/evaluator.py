"""Run code and extract metrics — the fixed evaluation boundary."""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RunResult:
    metric_value: float | None
    crashed: bool
    log: str
    duration_seconds: float
    tail: str  # last N lines, for crash diagnosis


class Evaluator:
    """Runs the target command, extracts the metric. This is the trust boundary —
    the LLM never modifies evaluation logic."""

    def __init__(self, run_command: str, metric_pattern: str, work_dir: Path, timeout: int):
        self.run_command = run_command
        self.metric_pattern = re.compile(metric_pattern)
        self.work_dir = work_dir
        self.timeout = timeout

    def run(self, log_file: Path) -> RunResult:
        start = time.time()
        try:
            result = subprocess.run(
                self.run_command,
                shell=True,
                cwd=self.work_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            log = result.stdout + "\n" + result.stderr
            crashed = result.returncode != 0
        except subprocess.TimeoutExpired:
            duration = time.time() - start
            return RunResult(
                metric_value=None,
                crashed=True,
                log=f"TIMEOUT after {duration:.0f}s (limit: {self.timeout}s)",
                duration_seconds=duration,
                tail=f"Process killed after {self.timeout}s timeout",
            )

        duration = time.time() - start

        # Write full log
        log_file.write_text(log)

        # Extract metric — last match wins (so final evaluation is used)
        metric_value = None
        for line in log.split("\n"):
            match = self.metric_pattern.search(line)
            if match:
                try:
                    metric_value = float(match.group(1))
                except (ValueError, IndexError):
                    pass

        lines = log.strip().split("\n")
        tail = "\n".join(lines[-50:])

        return RunResult(
            metric_value=metric_value,
            crashed=crashed or metric_value is None,
            log=log,
            duration_seconds=duration,
            tail=tail,
        )
