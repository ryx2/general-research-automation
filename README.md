# General Research Automation (GRA)

Autonomous code optimization using LLMs. Point it at any file or folder, and it iteratively improves any metric — line count, accuracy, speed, test scores — using [Claude Code](https://docs.anthropic.com/en/docs/claude-code) under the hood.

Inspired by [Karpathy's autoresearch](https://github.com/karpathy/autoresearch), generalized to optimize **any metric** on **any codebase**.

## How it works

```
You provide:        GRA auto-detects:        Then it loops:
  - target file       - run command            1. Claude Code modifies code
  - timeouts          - metric + pattern       2. Evaluate & extract metric
  - strategy          - direction              3. Keep improvements, discard regressions
                                               4. Repeat until time budget exhausted
```

- **Claude Code as the engine** — not raw API calls, but the full Claude Code agent with file reading, editing, and search tools
- **AI auto-configuration** — analyzes your code to determine the run command, metric, regex pattern, and optimization direction
- **Git as experiment backbone** — every modification is a commit; rejected changes are `git reset`
- **Full memory** — a TSV lab notebook logs every attempt so the LLM avoids repeating failures

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

### Requirements

- Python 3.10+
- `ANTHROPIC_API_KEY` environment variable
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code): `npm install -g @anthropic-ai/claude-code`

## Quick start

```bash
gra
```

Just 4 questions:

1. **Target** — file or folder the AI will optimize
2. **Per-run timeout** — how long each evaluation can take (e.g. `5m`)
3. **Total timeout** — how long the whole optimization runs (e.g. `2h`)
4. **Strategy notes** — optional free-form guidance (press enter to skip)

Everything else — run command, metric name, regex pattern, direction — is **auto-detected by AI**.

## Example: minimize lines of code

The `examples/minimize_lines/` directory contains a deliberately verbose Python function (~175 lines) that processes sales data. The goal: make it as short as possible while keeping all functionality and readability.

```bash
cd examples/minimize_lines
git init && git add -A && git commit -m "init"
gra
# Target: verbose_function.py
# Per-run timeout: 30s
# Total timeout: 10m
# Strategy: Retain all functionality but minimize line count. Don't remove comments. Keep it human readable.
```

GRA will:
1. Auto-detect that `evaluate.py` runs the tests and reports `line_count`
2. Use Claude Code to iteratively condense the function
3. Keep each change only if tests pass AND line count decreases
4. Generate a `progress.png` graph at the end

## Resume from config

Every run saves a `gra_config.json`. Reuse it:

```bash
gra --config path/to/gra_config.json
```

## Generate graph

```bash
gra --graph results.tsv
```

Generates `progress.png` showing metric improvement over experiments.

## Output

Each run produces:

- **Git branch** `gra/<timestamp>` — clean chain of validated improvements
- **results.tsv** — full lab notebook of every experiment
- **progress.png** — optimization progress graph
- **gra_config.json** — reproducible session config

## Advanced: full config

For full control, create `gra_config.json` manually:

```json
{
  "target": "train.py",
  "run_timeout": 300,
  "total_timeout": 28800,
  "run_command": "python train.py",
  "metric_name": "val_loss",
  "metric_pattern": "val_loss:\\s+([\\d.eE+-]+)",
  "direction": "minimize",
  "strategy": "Focus on optimizer and architecture changes",
  "readonly_files": ["data.py"],
  "model": "claude-sonnet-4-20250514",
  "max_fix_attempts": 3
}
```

Then: `gra --config gra_config.json`

## License

MIT
