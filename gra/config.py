"""Configuration for a GRA optimization session."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class Config:
    # What to optimize
    target_file: str  # path to the file the LLM will modify
    run_command: str  # shell command to execute (e.g. "python train.py")
    metric_name: str  # human-readable name of the metric
    metric_pattern: str  # grep pattern to extract metric from stdout (last match wins)
    direction: str  # "minimize" or "maximize"

    # Time budgets
    run_timeout: int  # seconds per run
    total_timeout: int  # seconds for entire optimization

    # Strategy (the "program.md" equivalent)
    strategy: str = ""  # free-form guidance for the LLM
    readonly_files: list[str] = field(default_factory=list)  # files the LLM can read but not modify

    # LLM config
    model: str = "claude-sonnet-4-20250514"
    max_fix_attempts: int = 3  # retries on crash before discarding

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2) + "\n")

    @classmethod
    def load(cls, path: Path) -> Config:
        data = json.loads(path.read_text())
        return cls(**data)
