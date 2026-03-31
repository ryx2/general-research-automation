"""Tests for Config save/load round-trip."""

from pathlib import Path

from gra.config import Config


def test_save_and_load(tmp_path: Path):
    config = Config(
        target="train.py",
        run_timeout=300,
        total_timeout=7200,
        run_command="python train.py",
        metric_name="val_loss",
        metric_pattern=r"val_loss:\s+([\d.]+)",
        direction="minimize",
        strategy="Try architectural changes first",
        readonly_files=["data.py", "utils.py"],
        model="claude-sonnet-4-20250514",
        max_fix_attempts=2,
    )
    path = tmp_path / "config.json"
    config.save(path)
    loaded = Config.load(path)

    assert loaded.target == config.target
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
        target="x.py",
        run_timeout=60,
        total_timeout=600,
    )
    assert config.strategy == ""
    assert config.readonly_files == []
    assert config.max_fix_attempts == 3
    assert config.run_command == ""
    assert config.metric_name == ""
    assert config.direction == ""


def test_backwards_compat_target_file(tmp_path: Path):
    """Old configs with target_file should load as target."""
    import json
    path = tmp_path / "old_config.json"
    path.write_text(json.dumps({
        "target_file": "train.py",
        "run_command": "python train.py",
        "metric_name": "loss",
        "metric_pattern": "loss:\\s+([\\d.]+)",
        "direction": "minimize",
        "run_timeout": 60,
        "total_timeout": 600,
    }))
    loaded = Config.load(path)
    assert loaded.target == "train.py"
