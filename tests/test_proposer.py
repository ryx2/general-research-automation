"""Tests for proposer response parsing and prompt building (no API calls)."""

from gra.proposer import Proposer, build_proposal_prompt


class TestParseResponse:
    """Test _parse_response without needing an API client."""

    def _parse(self, text: str, is_fix: bool = False) -> tuple[str, str]:
        # Call the unbound method directly — it doesn't use self.client
        return Proposer._parse_response(None, text, is_fix)

    def test_standard_format(self):
        text = (
            "DESCRIPTION: Use Adam optimizer instead of SGD\n"
            "CODE:\n"
            "```python\n"
            "import torch\n"
            "optimizer = torch.optim.Adam(model.parameters(), lr=0.001)\n"
            "```"
        )
        desc, code = self._parse(text)
        assert desc == "Use Adam optimizer instead of SGD"
        assert "Adam" in code
        assert "import torch" in code

    def test_code_block_without_language(self):
        text = (
            "DESCRIPTION: Double the learning rate\n"
            "CODE:\n"
            "```\n"
            "lr = 0.002\n"
            "```"
        )
        desc, code = self._parse(text)
        assert desc == "Double the learning rate"
        assert "lr = 0.002" in code

    def test_multiple_code_blocks_uses_last(self):
        text = (
            "DESCRIPTION: Refactor training loop\n\n"
            "Here's the old code:\n"
            "```\n"
            "old_code = True\n"
            "```\n\n"
            "And here's the new version:\n"
            "```python\n"
            "new_code = True\n"
            "```"
        )
        desc, code = self._parse(text)
        assert "new_code" in code
        assert "old_code" not in code

    def test_crash_fix_default_description(self):
        text = "```\nfixed_code = True\n```"
        desc, code = self._parse(text, is_fix=True)
        assert desc == "fix crash"
        assert "fixed_code" in code

    def test_description_case_insensitive(self):
        text = "description: lower case works\n```\ncode = 1\n```"
        desc, code = self._parse(text)
        assert desc == "lower case works"


class TestBuildPrompt:
    def test_basic_prompt_structure(self):
        messages = build_proposal_prompt(
            target_code="x = 1",
            target_file="train.py",
            metric_name="loss",
            direction="minimize",
            history="No experiments yet.",
            git_log="abc123 init",
            strategy="",
            readonly_contents={},
        )
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        content = messages[0]["content"]
        assert "train.py" in content
        assert "x = 1" in content
        assert "minimize" in content
        assert "DESCRIPTION" in content

    def test_includes_strategy(self):
        messages = build_proposal_prompt(
            target_code="x = 1",
            target_file="t.py",
            metric_name="loss",
            direction="minimize",
            history="",
            git_log="",
            strategy="Focus on optimizer changes",
            readonly_contents={},
        )
        assert "Focus on optimizer changes" in messages[0]["content"]

    def test_includes_readonly_files(self):
        messages = build_proposal_prompt(
            target_code="x = 1",
            target_file="t.py",
            metric_name="loss",
            direction="minimize",
            history="",
            git_log="",
            strategy="",
            readonly_contents={"utils.py": "def helper(): pass"},
        )
        content = messages[0]["content"]
        assert "utils.py" in content
        assert "def helper" in content

    def test_crash_context_changes_prompt(self):
        messages = build_proposal_prompt(
            target_code="x = 1",
            target_file="t.py",
            metric_name="loss",
            direction="minimize",
            history="",
            git_log="",
            strategy="",
            readonly_contents={},
            crash_context="NameError: name 'y' is not defined",
        )
        content = messages[0]["content"]
        assert "CRASH" in content
        assert "NameError" in content
        assert "DESCRIPTION" not in content  # crash prompt doesn't ask for description
