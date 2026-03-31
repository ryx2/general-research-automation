"""Tests for proposer prompt building and output parsing (no API calls)."""

import json

from gra.proposer import Proposer, build_proposal_prompt


class TestBuildPrompt:
    def test_basic_structure(self):
        prompt = build_proposal_prompt(
            target="train.py",
            metric_name="loss",
            direction="minimize",
            history="No experiments yet.",
            git_log="abc123 init",
            strategy="",
        )
        assert isinstance(prompt, str)
        assert "train.py" in prompt
        assert "minimize" in prompt
        assert "loss" in prompt
        assert "ONE focused modification" in prompt

    def test_includes_strategy(self):
        prompt = build_proposal_prompt(
            target="t.py",
            metric_name="loss",
            direction="minimize",
            history="",
            git_log="",
            strategy="Focus on optimizer changes",
        )
        assert "Focus on optimizer changes" in prompt

    def test_includes_readonly_files(self):
        prompt = build_proposal_prompt(
            target="t.py",
            metric_name="loss",
            direction="minimize",
            history="",
            git_log="",
            strategy="",
            readonly_files=["utils.py", "data.py"],
        )
        assert "utils.py" in prompt
        assert "data.py" in prompt
        assert "do NOT modify" in prompt

    def test_crash_context(self):
        prompt = build_proposal_prompt(
            target="t.py",
            metric_name="loss",
            direction="minimize",
            history="",
            git_log="",
            strategy="",
            crash_context="NameError: name 'y' is not defined",
        )
        assert "CRASH" in prompt
        assert "NameError" in prompt

    def test_folder_target(self):
        prompt = build_proposal_prompt(
            target="src/",
            metric_name="test_score",
            direction="maximize",
            history="",
            git_log="",
            strategy="",
        )
        assert "src/" in prompt
        assert "maximize" in prompt


class TestParseOutput:
    def _parse(self, raw: str) -> str:
        return Proposer._parse_output(None, raw)

    def test_json_result_format(self):
        raw = json.dumps({"result": "I changed the learning rate to 0.001", "cost_usd": 0.05})
        assert "learning rate" in self._parse(raw)

    def test_non_json_fallback(self):
        raw = "Some plain text response"
        assert self._parse(raw) == "Some plain text response"

    def test_empty_returns_default(self):
        assert self._parse("") == "modification"

    def test_json_with_empty_result(self):
        raw = json.dumps({"result": ""})
        assert self._parse(raw) == "modification"

    def test_multiline_takes_first_meaningful_line(self):
        raw = json.dumps({"result": "# Header\nI refactored the function\nMore details"})
        assert self._parse(raw) == "I refactored the function"

    def test_list_format(self):
        raw = json.dumps([
            {"role": "user", "content": "do something"},
            {"role": "assistant", "content": "I updated the optimizer settings"},
        ])
        assert "optimizer" in self._parse(raw)
