"""Configuration for a GRA optimization session."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class Config:
    # What to optimize
    target: str  # path to file or folder the LLM will modify

    # Time budgets
    run_timeout: int  # seconds per run
    total_timeout: int  # seconds for entire optimization

    # Auto-detected by AI (can be overridden via --config)
    run_command: str = ""  # shell command to execute
    metric_name: str = ""  # human-readable metric name
    metric_pattern: str = ""  # regex to extract metric from stdout
    direction: str = ""  # "minimize" or "maximize"

    # Strategy (optional)
    strategy: str = ""
    readonly_files: list[str] = field(default_factory=list)

    # LLM config
    model: str = "claude-sonnet-4-20250514"
    max_fix_attempts: int = 3

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2) + "\n")

    @classmethod
    def load(cls, path: Path) -> Config:
        data = json.loads(path.read_text())
        # Backwards compatibility
        if "target_file" in data and "target" not in data:
            data["target"] = data.pop("target_file")
        return cls(**data)
