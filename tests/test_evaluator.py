"""Tests for the Evaluator — metric extraction and run handling."""

from pathlib import Path

from gra.evaluator import Evaluator


def test_extract_metric_from_stdout(tmp_path: Path):
    """Run a command that prints a metric and verify extraction."""
    script = tmp_path / "run.py"
    script.write_text(
        'print("epoch 1 val_loss: 0.532")\n'
        'print("epoch 2 val_loss: 0.421")\n'
        'print("epoch 3 val_loss: 0.387")\n'
    )
    log_file = tmp_path / "run.log"
    evaluator = Evaluator(
        run_command=f"python3 {script}",
        metric_pattern=r"val_loss:\s+([\d.]+)",
        work_dir=tmp_path,
        timeout=30,
    )
    result = evaluator.run(log_file)

    assert not result.crashed
    # Last match wins — should be 0.387
    assert result.metric_value == 0.387
    assert result.duration_seconds > 0
    assert log_file.exists()


def test_last_match_wins(tmp_path: Path):
    """When multiple lines match, the last one is used."""
    script = tmp_path / "run.py"
    script.write_text(
        'print("score: 10")\n'
        'print("score: 20")\n'
        'print("score: 35")\n'
    )
    log_file = tmp_path / "run.log"
    evaluator = Evaluator(
        run_command=f"python3 {script}",
        metric_pattern=r"score:\s+([\d.]+)",
        work_dir=tmp_path,
        timeout=30,
    )
    result = evaluator.run(log_file)
    assert result.metric_value == 35.0


def test_no_metric_is_crash(tmp_path: Path):
    """If no metric line is found, treat as crash."""
    script = tmp_path / "run.py"
    script.write_text('print("hello world")\n')
    log_file = tmp_path / "run.log"
    evaluator = Evaluator(
        run_command=f"python3 {script}",
        metric_pattern=r"score:\s+([\d.]+)",
        work_dir=tmp_path,
        timeout=30,
    )
    result = evaluator.run(log_file)
    assert result.crashed
    assert result.metric_value is None


def test_nonzero_exit_is_crash(tmp_path: Path):
    """Non-zero exit code should be flagged as crash."""
    script = tmp_path / "run.py"
    script.write_text('raise ValueError("boom")\n')
    log_file = tmp_path / "run.log"
    evaluator = Evaluator(
        run_command=f"python3 {script}",
        metric_pattern=r"score:\s+([\d.]+)",
        work_dir=tmp_path,
        timeout=30,
    )
    result = evaluator.run(log_file)
    assert result.crashed
    assert "ValueError" in result.tail


def test_timeout(tmp_path: Path):
    """Command exceeding timeout should be killed."""
    script = tmp_path / "run.py"
    script.write_text('import time; time.sleep(60); print("score: 1")\n')
    log_file = tmp_path / "run.log"
    evaluator = Evaluator(
        run_command=f"python3 {script}",
        metric_pattern=r"score:\s+([\d.]+)",
        work_dir=tmp_path,
        timeout=2,
    )
    result = evaluator.run(log_file)
    assert result.crashed
    assert result.metric_value is None
    assert result.duration_seconds < 10  # should be ~2s, not 60


def test_scientific_notation(tmp_path: Path):
    """Metric in scientific notation should parse."""
    script = tmp_path / "run.py"
    script.write_text('print("loss: 3.5e-04")\n')
    log_file = tmp_path / "run.log"
    evaluator = Evaluator(
        run_command=f"python3 {script}",
        metric_pattern=r"loss:\s+([\d.eE+-]+)",
        work_dir=tmp_path,
        timeout=30,
    )
    result = evaluator.run(log_file)
    assert not result.crashed
    assert abs(result.metric_value - 0.00035) < 1e-8
