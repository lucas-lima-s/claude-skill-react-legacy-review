# Setup

This skill has no external dependencies at runtime - `SKILL.md` and the
files under `references/` are plain markdown, read directly by the agent
(Claude Code, Codex, agy or Cursor).
The only tooling involved is `scripts/check_rules.py`, used to validate the
catalog's structure during development and in CI.

## Requirements

- Python 3.11 or newer, for `scripts/check_rules.py` and the test suite.
- [uv](https://docs.astral.sh/uv/) for dependency management, or a plain
  virtual environment with `pip install -r requirements-dev.txt`.

No environment variables, API keys, or machine-specific paths are required
anywhere in this repository. All commands below are run from the repository
root and use only relative paths.

## Installing the skill

Clone the repository anywhere and expose the folder to each agent through
its skills directory, as a symlink or a copy, under the name
`react-legacy-review` (for example `~/.claude/skills/react-legacy-review`,
`~/.agents/skills/react-legacy-review` or
`~/.gemini/config/skills/react-legacy-review`).

```bash
git clone https://github.com/lucas-lima-s/claude-skill-react-legacy-review <skill-dir>
```

There is no skill-specific configuration file to edit.

## Installing development dependencies

With uv:

```bash
uv sync --dev
```

Without uv:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

## Running the checks locally

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run python scripts/check_rules.py references/checklist.md references/saga-patterns.md --min-rules 46
```

All four commands are also run in CI (`.github/workflows/ci.yml`) on every
push and pull request, across Python 3.11, 3.12, and 3.13, on both Ubuntu
and Windows.
