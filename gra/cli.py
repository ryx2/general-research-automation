"""Interactive CLI for General Research Automation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from .config import Config
from .loop import run_loop

console = Console()

BANNER = r"""
   ____ ____      _
  / ___|  _ \    / \
 | |  _| |_) |  / _ \
 | |_| |  _ <  / ___ \
  \____|_| \_\/_/   \_\

 General Research Automation
 Autonomous code optimization via LLMs
"""


def interactive_setup() -> tuple[Config, Path]:
    """Walk the user through configuring an optimization run."""
    console.print(Panel(BANNER, style="bold cyan"))

    # Target directory
    work_dir_str = Prompt.ask(
        "[bold]Working directory[/bold] (the git repo with your code)",
        default=".",
    )
    work_dir = Path(work_dir_str).resolve()
    if not work_dir.is_dir():
        console.print(f"[red]Directory not found: {work_dir}[/red]")
        sys.exit(1)
    if not (work_dir / ".git").is_dir():
        console.print(f"[yellow]Warning: {work_dir} is not a git repo. Initializing one.[/yellow]")
        import subprocess
        subprocess.run(["git", "init"], cwd=work_dir, check=True)

    # Target file
    target_file = Prompt.ask(
        "[bold]Target file[/bold] (the file the LLM will modify, relative to working dir)",
    )
    if not (work_dir / target_file).exists():
        console.print(f"[red]File not found: {work_dir / target_file}[/red]")
        sys.exit(1)

    # Run command
    run_command = Prompt.ask(
        "[bold]Run command[/bold] (shell command to execute your code)",
        default=f"python {target_file}",
    )

    # Metric
    metric_name = Prompt.ask(
        "[bold]Metric name[/bold] (what are you optimizing?)",
        default="score",
    )

    console.print(
        "[dim]The metric pattern is a regex applied to stdout. Use a capture group for the number.[/dim]\n"
        "[dim]Example: if your code prints 'val_loss: 0.342', use 'val_loss:\\s*([\\d.]+)'[/dim]"
    )
    default_pattern = metric_name + r"[:\s]+([\\d.eE+-]+)"
    metric_pattern = Prompt.ask(
        "[bold]Metric regex pattern[/bold] (must have one capture group for the number)",
        default=default_pattern,
    )

    direction = Prompt.ask(
        "[bold]Direction[/bold]",
        choices=["minimize", "maximize"],
        default="minimize",
    )

    # Time budgets
    run_timeout_str = Prompt.ask(
        "[bold]Time limit per run[/bold] (e.g. '5m', '300s', '1h')",
        default="5m",
    )
    run_timeout = _parse_duration(run_timeout_str)

    total_timeout_str = Prompt.ask(
        "[bold]Total optimization time[/bold] (e.g. '2h', '8h', '30m')",
        default="2h",
    )
    total_timeout = _parse_duration(total_timeout_str)

    # Strategy
    console.print(
        "\n[dim]Strategy notes are free-form guidance for the LLM — constraints, ideas to try,[/dim]\n"
        "[dim]things to avoid, domain knowledge. Like Karpathy's program.md. Press enter to skip.[/dim]"
    )
    strategy = Prompt.ask("[bold]Strategy notes[/bold]", default="")

    # Read-only files
    readonly_str = Prompt.ask(
        "[bold]Read-only reference files[/bold] (comma-separated, LLM can read but not modify)",
        default="",
    )
    readonly_files = [f.strip() for f in readonly_str.split(",") if f.strip()]

    # Model
    model = Prompt.ask(
        "[bold]LLM model[/bold]",
        default="claude-sonnet-4-20250514",
    )

    config = Config(
        target_file=target_file,
        run_command=run_command,
        metric_name=metric_name,
        metric_pattern=metric_pattern,
        direction=direction,
        run_timeout=run_timeout,
        total_timeout=total_timeout,
        strategy=strategy,
        readonly_files=readonly_files,
        model=model,
    )

    # Save config
    config_path = work_dir / "gra_config.json"
    config.save(config_path)
    console.print(f"\n[green]Config saved to {config_path}[/green]")

    return config, work_dir


def _parse_duration(s: str) -> int:
    """Parse a duration string like '5m', '2h', '300s' into seconds."""
    s = s.strip().lower()
    if s.endswith("h"):
        return int(float(s[:-1]) * 3600)
    if s.endswith("m"):
        return int(float(s[:-1]) * 60)
    if s.endswith("s"):
        return int(float(s[:-1]))
    return int(s)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="General Research Automation — autonomous code optimization via LLMs",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to gra_config.json to resume a previous session (skips interactive setup)",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="Working directory (used with --config)",
    )
    args = parser.parse_args()

    if args.config:
        config = Config.load(args.config)
        work_dir = args.work_dir or args.config.parent
        work_dir = work_dir.resolve()
        console.print(f"[green]Loaded config from {args.config}[/green]")
    else:
        config, work_dir = interactive_setup()

    # Confirm and go
    console.print()
    console.print(Panel(
        f"Target: [bold]{config.target_file}[/bold]\n"
        f"Command: [bold]{config.run_command}[/bold]\n"
        f"Metric: [bold]{config.metric_name}[/bold] ({config.direction})\n"
        f"Pattern: [bold]{config.metric_pattern}[/bold]\n"
        f"Per-run timeout: [bold]{config.run_timeout}s[/bold]\n"
        f"Total timeout: [bold]{config.total_timeout}s[/bold]\n"
        f"Model: [bold]{config.model}[/bold]",
        title="Configuration",
        style="cyan",
    ))

    if not Confirm.ask("\n[bold]Start optimization?[/bold]", default=True):
        console.print("[dim]Aborted.[/dim]")
        sys.exit(0)

    run_loop(config, work_dir)


if __name__ == "__main__":
    main()
