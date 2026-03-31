"""LLM-based code modification proposals — the search algorithm."""

from __future__ import annotations

from pathlib import Path

import anthropic


SYSTEM_PROMPT = """\
You are an autonomous research agent optimizing code to improve a metric.

## Your role
You modify the TARGET FILE to try to improve the metric. You operate in a loop:
1. Read the current code and experiment history
2. Propose a single, focused modification
3. The system runs the code and evaluates the result
4. If improved, your change is kept. If not, it's discarded.

## Rules
- Make ONE conceptual change per iteration. Don't combine unrelated changes.
- Be bold — try architectural changes, not just hyperparameter tweaks.
- Learn from history: don't repeat failed approaches, but do iterate on near-misses.
- If a small improvement adds significant complexity, it's probably not worth it.
- If you can delete code for equal or better results, that's always a win.
- NEVER modify how the metric is computed or reported — that's off limits.
- NEVER add code that special-cases the evaluation — optimize genuinely.
- Keep the code clean and readable.
"""


def build_proposal_prompt(
    target_code: str,
    target_file: str,
    metric_name: str,
    direction: str,
    history: str,
    git_log: str,
    strategy: str,
    readonly_contents: dict[str, str],
    crash_context: str | None = None,
) -> list[dict]:
    """Build the message list for the LLM to propose a code modification."""
    messages = []

    user_parts = []
    user_parts.append(f"## Target file: {target_file}\n```\n{target_code}\n```")

    if readonly_contents:
        for name, content in readonly_contents.items():
            user_parts.append(f"## Read-only reference: {name}\n```\n{content}\n```")

    user_parts.append(f"## Metric: {metric_name} (goal: {direction})")

    if strategy:
        user_parts.append(f"## Strategy notes from the human operator\n{strategy}")

    user_parts.append(f"## Experiment history (recent)\n```\n{history}\n```")
    user_parts.append(f"## Git log (kept improvements)\n```\n{git_log}\n```")

    if crash_context:
        user_parts.append(
            f"## CRASH — the last modification caused an error. Fix it.\n"
            f"```\n{crash_context}\n```\n"
            f"Reply with the fixed version of the target file."
        )
    else:
        user_parts.append(
            "## Task\n"
            "Propose the next modification to improve the metric. "
            "Reply with:\n"
            "1. A one-line DESCRIPTION of what you're changing and why\n"
            "2. The COMPLETE new version of the target file\n\n"
            "Format:\n"
            "DESCRIPTION: <your one-line description>\n"
            "CODE:\n```\n<entire file contents>\n```"
        )

    messages.append({"role": "user", "content": "\n\n".join(user_parts)})
    return messages


class Proposer:
    """Uses an LLM to propose code modifications."""

    def __init__(self, model: str):
        self.client = anthropic.Anthropic()
        self.model = model

    def propose(
        self,
        target_code: str,
        target_file: str,
        metric_name: str,
        direction: str,
        history: str,
        git_log: str,
        strategy: str,
        readonly_contents: dict[str, str],
        crash_context: str | None = None,
    ) -> tuple[str, str]:
        """Returns (description, new_code) for the proposed modification."""
        messages = build_proposal_prompt(
            target_code=target_code,
            target_file=target_file,
            metric_name=metric_name,
            direction=direction,
            history=history,
            git_log=git_log,
            strategy=strategy,
            readonly_contents=readonly_contents,
            crash_context=crash_context,
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=messages,
        )

        text = response.content[0].text
        return self._parse_response(text, crash_context is not None)

    def _parse_response(self, text: str, is_fix: bool) -> tuple[str, str]:
        """Parse the LLM response into (description, code)."""
        # Extract description
        description = "fix crash" if is_fix else "modification"
        for line in text.split("\n"):
            if line.strip().upper().startswith("DESCRIPTION:"):
                description = line.split(":", 1)[1].strip()
                break

        # Extract code block
        code = ""
        in_code = False
        code_lines = []
        for line in text.split("\n"):
            if line.strip().startswith("```") and in_code:
                in_code = False
                continue
            if in_code:
                code_lines.append(line)
            if line.strip().startswith("```") and not in_code:
                in_code = True
                code_lines = []

        if code_lines:
            code = "\n".join(code_lines)
        else:
            # Fallback: if no code block found, treat everything after CODE: as code
            parts = text.split("CODE:", 1)
            if len(parts) > 1:
                code = parts[1].strip()
            else:
                code = text  # last resort

        return description, code
