"""Auto-configure GRA settings by analyzing code with AI."""

from __future__ import annotations

import json
from pathlib import Path

import anthropic


_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".tox",
              "dist", "build", ".eggs"}
_SKIP_EXT = {".pyc", ".pyo", ".so", ".o", ".a", ".dylib", ".png", ".jpg",
             ".gif", ".ico", ".woff", ".ttf", ".bin", ".pkl", ".gz", ".zip"}


def auto_configure(target: str, work_dir: Path, strategy: str = "") -> dict:
    """Analyze target code and determine run_command, metric_name, metric_pattern, direction."""
    target_path = work_dir / target

    if target_path.is_file():
        code_context = f"File: {target}\n```\n{target_path.read_text()}\n```"
    elif target_path.is_dir():
        code_context = _read_directory(target_path, target)
    else:
        raise FileNotFoundError(f"Target not found: {target_path}")

    surrounding = _get_surrounding_files(work_dir, target_path)

    prompt = f"""Analyze this code and determine how to set up an automated optimization loop.

## Target (what the AI will modify)
{code_context}

## Other files in the project (for context, not modified)
{surrounding}

## Strategy from the user
{strategy if strategy else "No specific strategy provided — infer from the code what makes sense to optimize."}

## Your task
Determine four things:

1. **run_command**: A shell command that runs or tests the code AND prints a numeric metric to stdout.
   - The metric line must be in the format: `name: <number>`
   - If a test/evaluation script already exists in the project, use it.
   - If none exists, write a short inline command that validates the code works and measures something appropriate.

2. **metric_name**: A short snake_case name for the metric (e.g. "line_count", "accuracy", "runtime_seconds").

3. **metric_pattern**: A Python regex string with exactly ONE capture group that extracts the numeric value from stdout. Must match the output format of your run_command.

4. **direction**: Either "minimize" or "maximize".

Reply with ONLY a JSON object (no markdown, no explanation):
{{"run_command": "...", "metric_name": "...", "metric_pattern": "...", "direction": "..."}}"""

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()

    # Strip markdown code blocks if present
    if "```" in text:
        lines = text.split("\n")
        json_lines = []
        in_block = False
        for line in lines:
            if line.strip().startswith("```"):
                in_block = not in_block
                continue
            if in_block:
                json_lines.append(line)
        text = "\n".join(json_lines)

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(text[start:end])
        else:
            raise ValueError(f"Could not parse AI config response: {text}")

    for key in ("run_command", "metric_name", "metric_pattern", "direction"):
        if key not in result:
            raise ValueError(f"AI config response missing key: {key}")
    if result["direction"] not in ("minimize", "maximize"):
        raise ValueError(f"Invalid direction: {result['direction']}")

    return result


def _read_directory(dir_path: Path, rel_name: str, max_size: int = 50_000) -> str:
    parts = []
    total = 0
    for f in sorted(dir_path.rglob("*")):
        if not f.is_file():
            continue
        if any(p.startswith(".") for p in f.relative_to(dir_path).parts):
            continue
        if f.suffix in _SKIP_EXT:
            continue
        if total > max_size:
            parts.append("... (truncated)")
            break
        try:
            content = f.read_text()
            parts.append(f"File: {f.relative_to(dir_path.parent)}\n```\n{content}\n```")
            total += len(content)
        except (UnicodeDecodeError, PermissionError):
            continue
    return "\n\n".join(parts) if parts else f"Directory: {rel_name} (empty)"


def _get_surrounding_files(work_dir: Path, target_path: Path,
                           max_files: int = 10, max_size: int = 30_000) -> str:
    parts = []
    total = 0
    for f in sorted(work_dir.rglob("*")):
        if not f.is_file():
            continue
        rel_parts = f.relative_to(work_dir).parts
        if any(p in _SKIP_DIRS or p.startswith(".") for p in rel_parts):
            continue
        if f.suffix in _SKIP_EXT:
            continue
        if target_path.is_file() and f == target_path:
            continue
        if target_path.is_dir() and f.is_relative_to(target_path):
            continue
        if total > max_size or len(parts) >= max_files:
            break
        try:
            content = f.read_text()
            parts.append(f"File: {f.relative_to(work_dir)}\n```\n{content}\n```")
            total += len(content)
        except (UnicodeDecodeError, PermissionError):
            continue
    return "\n\n".join(parts) if parts else "No other files."
