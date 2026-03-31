"""Integration test — evaluator + tracker working together on a real script."""

import subprocess
import time
from pathlib import Path

import pytest

from gra.evaluator import Evaluator
from gra.tracker import ExperimentResult, Tracker


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Set up a mini git project with a script that reports a metric."""
    # Initialize git
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)

    # Create a simple optimization target
    (tmp_path / "solve.py").write_text(
        "# Simple function: compute x^2 - 4x + 5, report minimum\n"
        "x = 10\n"
        "result = x**2 - 4*x + 5\n"
        "print(f'score: {result}')\n"
    )
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True, check=True)
    return tmp_path


def test_baseline_then_manual_improvement(project: Path):
    """Simulate one cycle: baseline run, manual code change, evaluate, keep/discard."""
    results_file = project / "results.tsv"
    log_file = project / "run.log"

    tracker = Tracker(project, results_file, "gra/integration-test")
    evaluator = Evaluator(
        run_command="python3 solve.py",
        metric_pattern=r"score:\s+([\d.eE+-]+)",
        work_dir=project,
        timeout=10,
    )

    # 1. Baseline
    baseline = evaluator.run(log_file)
    assert not baseline.crashed
    assert baseline.metric_value == 65.0  # 10^2 - 4*10 + 5 = 65

    baseline_commit = tracker.get_current_commit()
    tracker.log_result(ExperimentResult(
        timestamp=time.time(), commit=baseline_commit,
        metric_value=baseline.metric_value, status="baseline",
        description="baseline", duration_seconds=baseline.duration_seconds,
    ))

    # 2. Apply an improvement (x=2 gives minimum of 1)
    (project / "solve.py").write_text(
        "x = 2\n"
        "result = x**2 - 4*x + 5\n"
        "print(f'score: {result}')\n"
    )
    commit_hash = tracker.commit_change("gra: set x=2")

    result = evaluator.run(log_file)
    assert not result.crashed
    assert result.metric_value == 1.0  # 4 - 8 + 5 = 1

    # 3. It's an improvement (minimizing), so keep it
    assert result.metric_value < baseline.metric_value
    tracker.log_result(ExperimentResult(
        timestamp=time.time(), commit=commit_hash,
        metric_value=result.metric_value, status="kept",
        description="set x=2", duration_seconds=result.duration_seconds,
    ))

    # 4. Verify tracking
    history = tracker.get_history()
    assert "baseline" in history
    assert "kept" in history

    lines = results_file.read_text().strip().split("\n")
    assert len(lines) == 3  # header + baseline + kept


def test_discard_bad_change(project: Path):
    """A change that worsens the metric should be discardable."""
    results_file = project / "results.tsv"
    log_file = project / "run.log"

    tracker = Tracker(project, results_file, "gra/discard-test")
    evaluator = Evaluator(
        run_command="python3 solve.py",
        metric_pattern=r"score:\s+([\d.eE+-]+)",
        work_dir=project,
        timeout=10,
    )

    # Baseline: x=10, score=65
    baseline = evaluator.run(log_file)
    parent_commit = tracker.get_current_commit()

    # Bad change: x=100, score=9605
    (project / "solve.py").write_text(
        "x = 100\n"
        "result = x**2 - 4*x + 5\n"
        "print(f'score: {result}')\n"
    )
    tracker.commit_change("gra: set x=100")

    result = evaluator.run(log_file)
    assert result.metric_value == 9605.0  # worse

    # Discard
    tracker.discard_to(parent_commit)

    # Verify code is restored
    code = (project / "solve.py").read_text()
    assert "x = 10" in code


def test_crash_recovery(project: Path):
    """A crashing script should be detected and the change discardable."""
    results_file = project / "results.tsv"
    log_file = project / "run.log"

    tracker = Tracker(project, results_file, "gra/crash-test")
    evaluator = Evaluator(
        run_command="python3 solve.py",
        metric_pattern=r"score:\s+([\d.eE+-]+)",
        work_dir=project,
        timeout=10,
    )

    parent_commit = tracker.get_current_commit()

    # Break the code
    (project / "solve.py").write_text("raise RuntimeError('intentional crash')\n")
    tracker.commit_change("gra: break it")

    result = evaluator.run(log_file)
    assert result.crashed
    assert "RuntimeError" in result.tail

    # Recover
    tracker.discard_to(parent_commit)
    restored = evaluator.run(log_file)
    assert not restored.crashed
    assert restored.metric_value == 65.0
