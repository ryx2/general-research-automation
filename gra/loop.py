"""The core optimization loop — hill climbing over code via LLM proposals."""

from __future__ import annotations

import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import Config
from .evaluator import Evaluator, RunResult
from .proposer import Proposer
from .tracker import ExperimentResult, Tracker

console = Console()


def is_improvement(new: float, old: float, direction: str) -> bool:
    if direction == "minimize":
        return new < old
    return new > old


def run_loop(config: Config, work_dir: Path) -> None:
    """Main optimization loop. Runs until total_timeout is exhausted."""
    results_file = work_dir / "results.tsv"
    log_file = work_dir / "run.log"
    branch_name = f"gra/{int(time.time())}"

    tracker = Tracker(work_dir, results_file, branch_name)
    evaluator = Evaluator(config.run_command, config.metric_pattern, work_dir, config.run_timeout)
    proposer = Proposer(config.model)

    target_path = work_dir / config.target_file
    readonly_contents: dict[str, str] = {}
    for rf in config.readonly_files:
        p = work_dir / rf
        if p.exists():
            readonly_contents[rf] = p.read_text()

    # --- Baseline run ---
    console.print(Panel("[bold]Running baseline...[/bold]", style="blue"))
    baseline = evaluator.run(log_file)
    if baseline.crashed or baseline.metric_value is None:
        console.print(f"[red]Baseline run failed![/red]\n{baseline.tail}")
        console.print("Fix your code so it runs successfully and reports the metric, then try again.")
        return

    best_metric = baseline.metric_value
    baseline_commit = tracker.get_current_commit()
    tracker.log_result(ExperimentResult(
        timestamp=time.time(),
        commit=baseline_commit,
        metric_value=best_metric,
        status="baseline",
        description="initial baseline run",
        duration_seconds=baseline.duration_seconds,
    ))

    console.print(f"[green]Baseline {config.metric_name}: {best_metric:.6f}[/green]")
    console.print(f"[dim]Direction: {config.direction} | Run timeout: {config.run_timeout}s | Total timeout: {config.total_timeout}s[/dim]")
    console.print()

    start_time = time.time()
    experiment_num = 0
    kept = 0
    discarded = 0
    crashes = 0

    # --- Main loop ---
    while True:
        elapsed = time.time() - start_time
        remaining = config.total_timeout - elapsed
        if remaining <= 0:
            break

        experiment_num += 1
        console.rule(f"[bold]Experiment {experiment_num}[/bold] ({elapsed/60:.0f}m elapsed, {remaining/60:.0f}m remaining)")

        # Read current state
        target_code = target_path.read_text()
        history = tracker.get_history()
        git_log = tracker.get_git_log()
        parent_commit = tracker.get_current_commit()

        # Ask LLM for a proposal
        console.print("[cyan]Asking LLM for a proposal...[/cyan]")
        try:
            description, new_code = proposer.propose(
                target_code=target_code,
                target_file=config.target_file,
                metric_name=config.metric_name,
                direction=config.direction,
                history=history,
                git_log=git_log,
                strategy=config.strategy,
                readonly_contents=readonly_contents,
            )
        except Exception as e:
            console.print(f"[red]LLM error: {e}[/red]")
            time.sleep(5)
            continue

        console.print(f"[yellow]Proposal:[/yellow] {description}")

        # Apply change
        target_path.write_text(new_code)
        try:
            commit_hash = tracker.commit_change(f"gra: {description}")
        except RuntimeError:
            # Nothing changed
            console.print("[dim]No actual code change — skipping[/dim]")
            continue

        # Run evaluation
        console.print("[cyan]Running evaluation...[/cyan]")
        result = evaluator.run(log_file)

        # Handle crash with retry
        if result.crashed:
            console.print(f"[red]CRASH[/red] — attempting fix...")
            fixed = False
            for fix_attempt in range(config.max_fix_attempts):
                try:
                    crash_code = target_path.read_text()
                    fix_desc, fix_code = proposer.propose(
                        target_code=crash_code,
                        target_file=config.target_file,
                        metric_name=config.metric_name,
                        direction=config.direction,
                        history=history,
                        git_log=git_log,
                        strategy=config.strategy,
                        readonly_contents=readonly_contents,
                        crash_context=result.tail,
                    )
                    target_path.write_text(fix_code)
                    tracker.commit_change(f"gra: fix attempt {fix_attempt + 1}: {fix_desc}")
                    result = evaluator.run(log_file)
                    if not result.crashed and result.metric_value is not None:
                        fixed = True
                        break
                except Exception as e:
                    console.print(f"[red]Fix attempt failed: {e}[/red]")

            if not fixed:
                console.print("[red]Could not fix — discarding[/red]")
                tracker.discard_to(parent_commit)
                tracker.log_result(ExperimentResult(
                    timestamp=time.time(),
                    commit=commit_hash,
                    metric_value=None,
                    status="crash",
                    description=description,
                    duration_seconds=result.duration_seconds,
                ))
                crashes += 1
                _print_status(experiment_num, kept, discarded, crashes, best_metric, config)
                continue

        # Decide: keep or discard
        assert result.metric_value is not None
        if is_improvement(result.metric_value, best_metric, config.direction):
            delta = result.metric_value - best_metric
            console.print(
                f"[bold green]KEPT[/bold green] {config.metric_name}: "
                f"{best_metric:.6f} -> {result.metric_value:.6f} (delta: {delta:+.6f})"
            )
            best_metric = result.metric_value
            kept += 1
            tracker.log_result(ExperimentResult(
                timestamp=time.time(),
                commit=tracker.get_current_commit(),
                metric_value=result.metric_value,
                status="kept",
                description=description,
                duration_seconds=result.duration_seconds,
            ))
        else:
            delta = result.metric_value - best_metric
            console.print(
                f"[dim]DISCARDED[/dim] {config.metric_name}: "
                f"{result.metric_value:.6f} (delta: {delta:+.6f})"
            )
            tracker.discard_to(parent_commit)
            discarded += 1
            tracker.log_result(ExperimentResult(
                timestamp=time.time(),
                commit=commit_hash,
                metric_value=result.metric_value,
                status="discarded",
                description=description,
                duration_seconds=result.duration_seconds,
            ))

        _print_status(experiment_num, kept, discarded, crashes, best_metric, config)

    # --- Done ---
    console.print()
    console.print(Panel(
        f"[bold green]Optimization complete![/bold green]\n\n"
        f"Experiments: {experiment_num}\n"
        f"Kept: {kept} | Discarded: {discarded} | Crashes: {crashes}\n"
        f"Best {config.metric_name}: {best_metric:.6f}\n"
        f"Branch: {branch_name}\n"
        f"Results: {results_file}",
        title="GRA Summary",
        style="green",
    ))


def _print_status(exp: int, kept: int, discarded: int, crashes: int, best: float, config: Config) -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("Experiments", str(exp))
    table.add_row("Kept / Discarded / Crashes", f"{kept} / {discarded} / {crashes}")
    table.add_row(f"Best {config.metric_name}", f"{best:.6f}")
    console.print(table)
