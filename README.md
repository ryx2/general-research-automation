# General Research Automation (GRA)

Autonomous code optimization using LLMs. Inspired by [Karpathy's autoresearch](https://github.com/karpathy/autoresearch), generalized to optimize **any metric** by running **any code**.

You point it at a file, tell it what metric to optimize, and walk away. An LLM proposes modifications, the system evaluates them, keeps improvements, discards regressions, and repeats — indefinitely.

## Key ideas (from autoresearch, generalized)

- **Human writes strategy, agent writes code** — you provide constraints and goals in plain English, the LLM modifies source code
- **Fixed evaluation as trust boundary** — the metric extraction is immutable; the LLM can't game it
- **Git as experiment backbone** — every modification is a commit; rejected changes are `git reset`
- **LLM as the search algorithm** — not random mutation, but semantically informed code modification that learns from experiment history
- **Hill climbing with full memory** — a TSV lab notebook logs every attempt (kept, discarded, crashed) so the LLM avoids repeating failures

## Install

```bash
pip install general-research-automation
```

Or from source:

```bash
git clone https://github.com/ryx2/general-research-automation.git
cd general-research-automation
pip install -e .
```

## Requirements

- Python 3.10+
- An `ANTHROPIC_API_KEY` environment variable
- A git repo with code you want to optimize

## Usage

### Interactive mode

```bash
gra
```

The CLI walks you through setup:

1. **Working directory** — the git repo with your code
2. **Target file** — the file the LLM will modify
3. **Run command** — how to execute your code (e.g., `python train.py`)
4. **Metric name** — what you're optimizing (e.g., `val_loss`, `accuracy`, `throughput`)
5. **Metric pattern** — regex to extract the metric from stdout (e.g., `val_loss:\s+([\d.]+)`)
6. **Direction** — minimize or maximize
7. **Per-run timeout** — how long each evaluation can take (e.g., `5m`)
8. **Total timeout** — how long the whole optimization runs (e.g., `8h`)
9. **Strategy notes** — free-form guidance for the LLM (optional)

Then it runs autonomously until the time budget is exhausted.

### Resume from config

```bash
gra --config path/to/gra_config.json
```

## How it works

```
LOOP:
  1. Read current code + experiment history
  2. LLM proposes a single focused modification
  3. Git commit the change
  4. Run the code, extract metric from stdout
  5. If metric improved → KEEP (advance the branch)
  6. If metric worse or crash → DISCARD (git reset)
  7. Log everything to results.tsv
  8. Repeat until time budget exhausted
```

## Output

- **Git branch** `gra/<timestamp>` — clean chain of validated improvements
- **results.tsv** — full lab notebook of every experiment (kept, discarded, crashed)
- **run.log** — stdout/stderr from the last run
- **gra_config.json** — reproducible session config

## Examples

### Optimize a training script

```bash
cd my-ml-project
gra
# Target file: train.py
# Run command: python train.py
# Metric: val_loss
# Pattern: val_loss:\s+([\d.eE+-]+)
# Direction: minimize
# Per-run timeout: 5m
# Total timeout: 8h
```

### Optimize for speed

```bash
gra
# Target file: solver.py
# Run command: python benchmark.py
# Metric: throughput
# Pattern: throughput:\s+([\d.]+)
# Direction: maximize
# Per-run timeout: 2m
# Total timeout: 4h
```

### Optimize test scores

```bash
gra
# Target file: solution.py
# Run command: python grade.py
# Metric: score
# Pattern: score:\s+([\d.]+)
# Direction: maximize
# Per-run timeout: 30s
# Total timeout: 1h
```

## License

MIT
