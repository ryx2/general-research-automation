"""Tests for the Tracker — git operations and TSV logging."""

import subprocess
import time
from pathlib import Path

import pytest

from gra.tracker import ExperimentResult, Tracker


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repo with an initial commit."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)
    (tmp_path / "code.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True, check=True)
    return tmp_path


def test_creates_branch(git_repo: Path):
    results_file = git_repo / "results.tsv"
    tracker = Tracker(git_repo, results_file, "gra/test-branch")

    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=git_repo, capture_output=True, text=True,
    )
    assert result.stdout.strip() == "gra/test-branch"


def test_creates_results_file(git_repo: Path):
    results_file = git_repo / "results.tsv"
    Tracker(git_repo, results_file, "gra/test")
    assert results_file.exists()
    header = results_file.read_text().strip()
    assert "timestamp" in header
    assert "metric" in header


def test_commit_and_get_hash(git_repo: Path):
    results_file = git_repo / "results.tsv"
    tracker = Tracker(git_repo, results_file, "gra/test")

    (git_repo / "code.py").write_text("x = 2\n")
    commit_hash = tracker.commit_change("change x to 2")
    assert len(commit_hash) >= 7  # short hash


def test_discard_resets_file(git_repo: Path):
    results_file = git_repo / "results.tsv"
    tracker = Tracker(git_repo, results_file, "gra/test")

    parent = tracker.get_current_commit()
    (git_repo / "code.py").write_text("x = 999\n")
    tracker.commit_change("bad change")
    assert (git_repo / "code.py").read_text() == "x = 999\n"

    tracker.discard_to(parent)
    assert (git_repo / "code.py").read_text() == "x = 1\n"


def test_log_result_appends_to_tsv(git_repo: Path):
    results_file = git_repo / "results.tsv"
    tracker = Tracker(git_repo, results_file, "gra/test")

    tracker.log_result(ExperimentResult(
        timestamp=1000000.0,
        commit="abc1234",
        metric_value=0.42,
        status="kept",
        description="test change",
        duration_seconds=5.3,
    ))
    tracker.log_result(ExperimentResult(
        timestamp=1000010.0,
        commit="def5678",
        metric_value=None,
        status="crash",
        description="bad change",
        duration_seconds=2.1,
    ))

    lines = results_file.read_text().strip().split("\n")
    assert len(lines) == 3  # header + 2 results
    assert "0.420000" in lines[1]
    assert "crash" in lines[2]
    assert "N/A" in lines[2]


def test_get_history(git_repo: Path):
    results_file = git_repo / "results.tsv"
    tracker = Tracker(git_repo, results_file, "gra/test")

    assert tracker.get_history() == "No experiments yet."

    tracker.log_result(ExperimentResult(
        timestamp=time.time(), commit="aaa", metric_value=1.0,
        status="kept", description="first", duration_seconds=1.0,
    ))
    history = tracker.get_history()
    assert "timestamp" in history  # header present
    assert "first" in history


def test_get_git_log(git_repo: Path):
    results_file = git_repo / "results.tsv"
    tracker = Tracker(git_repo, results_file, "gra/test")
    log = tracker.get_git_log()
    assert "init" in log
