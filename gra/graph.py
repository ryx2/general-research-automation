"""Generate optimization progress graphs from results.tsv."""

from __future__ import annotations

import csv
from pathlib import Path


def generate_graph(results_file: Path, output_file: Path | None = None,
                   metric_name: str = "metric") -> Path:
    """Generate a progress graph from results.tsv. Returns path to saved PNG."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if output_file is None:
        output_file = results_file.parent / "progress.png"

    rows = []
    with open(results_file) as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            rows.append(row)

    if not rows:
        raise ValueError("No results to plot")

    kept_x, kept_y = [], []
    discarded_x, discarded_y = [], []
    crash_x = []
    baseline_x, baseline_y = [], []

    best_so_far = []
    current_best = None

    for i, row in enumerate(rows):
        status = row["status"]
        metric = row["metric"]

        if metric != "N/A":
            val = float(metric)
            if status == "baseline":
                baseline_x.append(i)
                baseline_y.append(val)
                current_best = val
            elif status == "kept":
                kept_x.append(i)
                kept_y.append(val)
                current_best = val
            elif status == "discarded":
                discarded_x.append(i)
                discarded_y.append(val)
        else:
            crash_x.append(i)

        best_so_far.append(current_best)

    fig, ax = plt.subplots(figsize=(12, 6))

    if baseline_x:
        ax.scatter(baseline_x, baseline_y, color="blue", marker="D",
                   s=100, zorder=5, label="Baseline")
    if kept_x:
        ax.scatter(kept_x, kept_y, color="green", marker="o",
                   s=60, zorder=4, label="Kept")
    if discarded_x:
        ax.scatter(discarded_x, discarded_y, color="red", marker="x",
                   s=40, zorder=3, alpha=0.5, label="Discarded")
    if crash_x:
        for cx in crash_x:
            ax.axvline(x=cx, color="orange", alpha=0.3, linewidth=1)
        ax.axvline(x=crash_x[0], color="orange", alpha=0.3,
                   linewidth=1, label="Crash")

    # Best-so-far line
    experiments = list(range(len(rows)))
    ax.plot(experiments, best_so_far, color="green", linewidth=2,
            alpha=0.7, linestyle="--", label="Best so far")

    ax.set_xlabel("Experiment #", fontsize=12)
    ax.set_ylabel(metric_name, fontsize=12)
    ax.set_title(f"GRA Optimization Progress", fontsize=14)
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    plt.close()

    return output_file
