"""Tests for Config save/load round-trip."""

from pathlib import Path

from gra.config import Config


def test_save_and_load(tmp_path: Path):
    config = Config(
        target_file="train.py",
        run_command="python train.py",
        metric_name="val_loss",
        metric_pattern=r"val_loss:\s+([\d.]+)",
        direction="minimize",
        run_timeout=300,
        total_timeout=7200,
        strategy="Try architectural changes first",
        readonly_files=["data.py", "utils.py"],
        model="claude-sonnet-4-20250514",
        max_fix_attempts=2,
    )
    path = tmp_path / "config.json"
    config.save(path)
    loaded = Config.load(path)

    assert loaded.target_file == config.target_file
    assert loaded.run_command == config.run_command
    assert loaded.metric_name == config.metric_name
    assert loaded.metric_pattern == config.metric_pattern
    assert loaded.direction == config.direction
    assert loaded.run_timeout == config.run_timeout
    assert loaded.total_timeout == config.total_timeout
    assert loaded.strategy == config.strategy
    assert loaded.readonly_files == config.readonly_files
    assert loaded.model == config.model
    assert loaded.max_fix_attempts == config.max_fix_attempts


def test_defaults():
    config = Config(
        target_file="x.py",
        run_command="python x.py",
        metric_name="score",
        metric_pattern=r"score:\s+([\d.]+)",
        direction="maximize",
        run_timeout=60,
        total_timeout=600,
    )
    assert config.strategy == ""
    assert config.readonly_files == []
    assert config.max_fix_attempts == 3
