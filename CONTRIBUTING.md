# Contributing

## Adding or editing a rule

Every rule in `references/checklist.md` and `references/saga-patterns.md`
must follow this exact shape:

`````markdown
### RL-<CATEGORY>-<NN> - <title>

**Impact:** one of bug, rerender, bundle, perf, maintainability
**Symptom:** an observable, concrete symptom - not a restatement of the rule.

```jsx
// avoid
<code that triggers the rule>
```

```jsx
// prefer
<code that avoids it>
```

**Accept when:** the specific condition under which the avoided pattern is
actually correct, or `never` when there is none.
`````

Rule ids must be contiguous per category (no gaps, no reused numbers) and
unique across both files. Run the validator after any change:

```bash
uv run python scripts/check_rules.py references/checklist.md references/saga-patterns.md --min-rules 46
```

## The style deny-list

`scripts/check_rules.py` fails if `next/`, `useTransition`,
`useDeferredValue`, `useEffectEvent`, `createRoot`, `Server Component`,
`RSC`, or `app router` appear anywhere outside
`references/legacy-constraints.md`. That file is the one place these terms
are the explicit subject (documenting what React 16.14 does not have);
everywhere else, their presence signals advice that silently assumes a
newer React version or a server framework. Do not add employer names,
internal tool names, or component names to this list - it exists to keep
advice version-accurate, not to encode anything project-specific.

## Code style

- Python: stdlib only in `scripts/check_rules.py`, `from __future__ import
  annotations`, PEP 585/604 type hints, no inline comments. Formatted and
  linted with `ruff`.
- JavaScript/JSX examples: no build step, no inline comments beyond the
  `// avoid` and `// prefer` markers the rule format requires.
- All prose in English.

## Tests

```bash
uv run pytest -q
```

Add a fixture under `tests/fixtures/` for any new failure mode the validator
should catch, and a corresponding test in `tests/test_check_rules.py`.

## Pull requests

Run the full local check sequence before opening a pull request:

```bash
uv sync --dev
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run python scripts/check_rules.py references/checklist.md references/saga-patterns.md --min-rules 46
```
