"""LLM-based code modification proposals using Claude Code."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def build_proposal_prompt(
    target: str,
    metric_name: str,
    direction: str,
    history: str,
    git_log: str,
    strategy: str,
    readonly_files: list[str] | None = None,
    crash_context: str | None = None,
) -> str:
    """Build the prompt for Claude Code to propose a modification."""
    parts = [
        f"You are optimizing `{target}` to {direction} the metric `{metric_name}`.",
        "Make ONE focused modification to improve the metric.",
        "",
        "Rules:",
        "- Make ONE conceptual change per iteration — don't combine unrelated changes",
        "- Be bold — try meaningful structural changes, not just trivial tweaks",
        "- Learn from history: don't repeat failed approaches, iterate on near-misses",
        "- NEVER modify how the metric is computed or reported",
        "- NEVER add code that special-cases the evaluation",
        "- Keep the code clean and readable",
        f"- Only modify files within: {target}",
        "",
    ]

    if readonly_files:
        parts.append(f"You may read these for context (do NOT modify): {', '.join(readonly_files)}")
        parts.append("")

    if strategy:
        parts.append("## Strategy notes from the human operator")
        parts.append(strategy)
        parts.append("")

    parts.append("## Experiment history (recent)")
    parts.append(f"```\n{history}\n```")
    parts.append("")

    parts.append("## Git log (kept improvements)")
    parts.append(f"```\n{git_log}\n```")
    parts.append("")

    if crash_context:
        parts.append("## CRASH — the last modification caused an error. Fix it.")
        parts.append(f"```\n{crash_context}\n```")
        parts.append("Fix the code to resolve this error.")
    else:
        parts.append("Read the target file(s), then make your modification.")
        parts.append("After editing, state what you changed in one sentence.")

    return "\n".join(parts)


class Proposer:
    """Uses Claude Code to propose and apply code modifications directly."""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model

    def propose(
        self,
        target: str,
        metric_name: str,
        direction: str,
        history: str,
        git_log: str,
        strategy: str,
        work_dir: Path,
        readonly_files: list[str] | None = None,
        crash_context: str | None = None,
    ) -> str:
        """Run Claude Code to modify the target. Returns description of changes."""
        prompt = build_proposal_prompt(
            target=target,
            metric_name=metric_name,
            direction=direction,
            history=history,
            git_log=git_log,
            strategy=strategy,
            readonly_files=readonly_files,
            crash_context=crash_context,
        )

        result = subprocess.run(
            [
                "claude", "-p", prompt,
                "--output-format", "json",
                "--model", self.model,
                "--allowedTools", "Edit,Read,Write,Glob,Grep",
                "--max-turns", "20",
            ],
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Claude Code error: {result.stderr[:500]}")

        return self._parse_output(result.stdout)

    def _parse_output(self, raw: str) -> str:
        """Extract a one-line description from Claude Code's JSON output."""
        try:
            output = json.loads(raw)
        except json.JSONDecodeError:
            return raw.strip().split("\n")[0][:200] if raw.strip() else "modification"

        # Claude Code JSON: {"result": "...", "cost_usd": ..., ...}
        if isinstance(output, dict):
            text = output.get("result", "")
        elif isinstance(output, list):
            text = ""
            for msg in reversed(output):
                if isinstance(msg, dict) and msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        text = content
                    elif isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                text = block.get("text", "")
                    break
        else:
            text = str(output)

        for line in text.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("```"):
                return line[:200]

        return "modification"
