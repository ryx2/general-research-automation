"""Experiment tracking via git and TSV logging."""

from __future__ import annotations

import csv
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExperimentResult:
    timestamp: float
    commit: str
    metric_value: float | None
    status: str  # "kept" | "discarded" | "crash"
    description: str
    duration_seconds: float


class Tracker:
    """Manages git commits and results.tsv for experiment tracking."""

    def __init__(self, work_dir: Path, results_file: Path, branch_name: str):
        self.work_dir = work_dir
        self.results_file = results_file
        self.branch_name = branch_name
        self._ensure_branch()
        self._ensure_results_file()

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.work_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout.strip()

    def _ensure_branch(self) -> None:
        try:
            current = self._git("branch", "--show-current")
        except RuntimeError:
            # No commits yet — make an initial commit
            self._git("add", "-A")
            self._git("commit", "--allow-empty", "-m", "gra: initial state")
            current = self._git("branch", "--show-current")

        if current != self.branch_name:
            try:
                self._git("checkout", "-b", self.branch_name)
            except RuntimeError:
                self._git("checkout", self.branch_name)

    def _ensure_results_file(self) -> None:
        if not self.results_file.exists():
            with open(self.results_file, "w", newline="") as f:
                writer = csv.writer(f, delimiter="\t")
                writer.writerow(["timestamp", "commit", "metric", "status", "duration_s", "description"])

    def get_current_commit(self) -> str:
        return self._git("rev-parse", "--short", "HEAD")

    def commit_change(self, message: str) -> str:
        self._git("add", "-A")
        self._git("commit", "-m", message)
        return self.get_current_commit()

    def discard_to(self, commit: str) -> None:
        self._git("reset", "--hard", commit)

    def log_result(self, result: ExperimentResult) -> None:
        with open(self.results_file, "a", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow([
                f"{result.timestamp:.0f}",
                result.commit,
                f"{result.metric_value:.6f}" if result.metric_value is not None else "N/A",
                result.status,
                f"{result.duration_seconds:.1f}",
                result.description,
            ])

    def get_history(self, last_n: int = 30) -> str:
        """Return recent experiment history as a string for LLM context."""
        if not self.results_file.exists():
            return "No experiments yet."
        lines = self.results_file.read_text().strip().split("\n")
        if len(lines) <= 1:
            return "No experiments yet."
        header = lines[0]
        recent = lines[-last_n:] if len(lines) > last_n + 1 else lines[1:]
        return header + "\n" + "\n".join(recent)

    def get_git_log(self, n: int = 20) -> str:
        try:
            return self._git("log", "--oneline", f"-{n}")
        except RuntimeError:
            return "No commits yet."
