"""Interactive CLI for General AutoResearch."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from .auto_config import auto_configure
from .config import Config
from .loop import run_loop

console = Console()

BANNER = r"""
   ____ ____      _
  / ___|  _ \    / \
 | |  _| |_) |  / _ \
 | |_| |  _ <  / ___ \
  \____|_| \_\/_/   \_\

 General AutoResearch
 Autonomous code optimization via LLMs
"""


def interactive_setup() -> tuple[Config, Path]:
    """Walk the user through configuring an optimization run — just 4 questions."""
    console.print(Panel(BANNER, style="bold cyan"))

    # 1. Working directory
    work_dir_str = Prompt.ask(
        "[bold]Working directory[/bold] (git repo with your code)",
        default=".",
    )
    work_dir = Path(work_dir_str).resolve()
    if not work_dir.is_dir():
        console.print(f"[red]Directory not found: {work_dir}[/red]")
        sys.exit(1)
    if not (work_dir / ".git").is_dir():
        console.print("[yellow]Not a git repo — initializing one.[/yellow]")
        import subprocess
        subprocess.run(["git", "init"], cwd=work_dir, check=True)

    # 2. Target file or folder
    target = Prompt.ask(
        "[bold]Target[/bold] (file or folder the AI will optimize)",
    )
    target_path = work_dir / target
    if not target_path.exists():
        console.print(f"[red]Not found: {target_path}[/red]")
        sys.exit(1)

    # 3. Per-run timeout
    run_timeout_str = Prompt.ask(
        "[bold]Per-run timeout[/bold] (e.g. '5m', '300s', '1h')",
        default="5m",
    )
    run_timeout = _parse_duration(run_timeout_str)

    # 4. Total timeout
    total_timeout_str = Prompt.ask(
        "[bold]Total optimization time[/bold] (e.g. '2h', '8h', '30m')",
        default="2h",
    )
    total_timeout = _parse_duration(total_timeout_str)

    # 5. Strategy (optional)
    console.print(
        "\n[dim]Strategy notes: constraints, goals, things to try/avoid. Press enter to skip.[/dim]"
    )
    strategy = Prompt.ask("[bold]Strategy notes[/bold] (optional)", default="")

    # Auto-detect run command, metric, pattern, direction
    console.print("\n[cyan]Analyzing code to auto-configure...[/cyan]")
    try:
        auto = auto_configure(target, work_dir, strategy)
    except Exception as e:
        console.print(f"[red]Auto-configuration failed: {e}[/red]")
        sys.exit(1)

    console.print(f"  Run command: [bold]{auto['run_command']}[/bold]")
    console.print(f"  Metric: [bold]{auto['metric_name']}[/bold] ({auto['direction']})")
    console.print(f"  Pattern: [bold]{auto['metric_pattern']}[/bold]")

    config = Config(
        target=target,
        run_timeout=run_timeout,
        total_timeout=total_timeout,
        run_command=auto["run_command"],
        metric_name=auto["metric_name"],
        metric_pattern=auto["metric_pattern"],
        direction=auto["direction"],
        strategy=strategy,
    )

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
        description="GRA — autonomous code optimization via LLMs",
    )
    parser.add_argument("--config", type=Path, help="Resume from gra_config.json")
    parser.add_argument("--work-dir", type=Path, help="Working directory (with --config)")
    parser.add_argument("--graph", type=Path, help="Generate graph from results.tsv")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    if args.graph:
        from .graph import generate_graph
        out = generate_graph(args.graph)
        console.print(f"[green]Graph saved to {out}[/green]")
        return

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
        f"Target: [bold]{config.target}[/bold]\n"
        f"Command: [bold]{config.run_command}[/bold]\n"
        f"Metric: [bold]{config.metric_name}[/bold] ({config.direction})\n"
        f"Pattern: [bold]{config.metric_pattern}[/bold]\n"
        f"Per-run timeout: [bold]{config.run_timeout}s[/bold]\n"
        f"Total timeout: [bold]{config.total_timeout}s[/bold]\n"
        f"Model: [bold]{config.model}[/bold]",
        title="Configuration",
        style="cyan",
    ))

    if not args.yes and not Confirm.ask("\n[bold]Start optimization?[/bold]", default=True):
        console.print("[dim]Aborted.[/dim]")
        sys.exit(0)

    run_loop(config, work_dir)


if __name__ == "__main__":
    main()
