# react-legacy-review

A Claude Code skill: a review checklist for legacy React 16 plus Redux-Saga
browser-rendered applications, organized by failure mode instead of by file
type, with a script that machine-validates the catalog's structure.

## Why

Most React guidance published today - blog posts, official examples, model
training data - assumes React 18's concurrent renderer or a server
framework's rendering model. Neither exists in a webpack-bundled, statically
hosted, browser-rendered React 16.14 codebase still running Redux-Saga. A
reviewer (human or an LLM) that does not know this ends up recommending APIs
the running application cannot use, or missing the specific bugs this
version's actual constraints produce.

This catalog is written for what React 16.14 and Redux-Saga actually
support: 53 rules across 8 categories, each with a symptom you can observe
while reading a diff, a bad and a good code example, and an explicit
`Accept when` clause for the cases where the pattern the rule warns about is
the right call anyway.

## Installation

Clone this repository and expose it as `react-legacy-review` in the skills
directory of each agent you use (Claude Code, Codex, agy or Cursor), as a
symlink or a copy:

```bash
git clone https://github.com/lucas-lima-s/claude-skill-react-legacy-review <skill-dir>
```

The agent picks up `SKILL.md` on the next session; no further configuration
is required.

## Usage

Ask Claude to review a React or Redux-Saga diff in a legacy codebase, for
example:

- "review this React component against the legacy checklist"
- "React 16 review of `TicketQueue.jsx`"
- "redux saga review of the checkout flow"

Claude reads `SKILL.md`, applies the rules whose categories match what the
diff touches, and reports each finding with the rule id, `file:line`, the
observed symptom, and the concrete fix. See `SKILL.md` for the full output
contract.

## Rules by category

| Category | Count | Covers |
|---|---|---|
| `RL-RENDER` | 10 | Component identity, render cost, list key stability |
| `RL-EFFECT` | 7 | Effect scope, dependency correctness, cleanup |
| `RL-SAGA` | 9 | Generator concurrency, cancellation, saga lifecycle |
| `RL-STATE` | 6 | Redux store shape, selector cost, serializability |
| `RL-BUNDLE` | 5 | What ships in the initial download |
| `RL-DOM` | 5 | Direct DOM cost: list size, listener count, layout thrash |
| `RL-JS` | 5 | Plain JavaScript cost on a hot path |
| `RL-COMPAT` | 6 | APIs and assumptions React 16.14 does not support |
| **Total** | **53** | |

## A sample rule

`````markdown
### RL-EFFECT-03 - Every subscription needs a matching cleanup

**Impact:** bug
**Symptom:** navigating away from `TicketList` and back doubles the frequency
of a handler firing on the next update, because the previous subscription
was never removed.

```jsx
// avoid
useEffect(() => {
  socket.on('ticket:update', handleUpdate)
}, [])
```

```jsx
// prefer
useEffect(() => {
  socket.on('ticket:update', handleUpdate)
  return () => socket.off('ticket:update', handleUpdate)
}, [])
```

**Accept when:** the subscription target is the module's own top-level
singleton that must live for the app's entire lifetime (a global error
logger registered once at boot) - never inside a component that mounts and
unmounts more than once.
`````

## Validating the catalog

`scripts/check_rules.py` parses `references/checklist.md` and
`references/saga-patterns.md` and checks: the `RL-<CAT>-<NN>` id pattern,
unique ids, contiguous numbering per category, a `**Impact:**` field with an
allowed value, a `**Symptom:**` field, an `**Accept when:**` field, at least
one `// avoid` and one `// prefer` fenced code block, no empty fenced block,
and a style deny-list that keeps React-18-only or server-framework-only
terms (`useTransition`, `useDeferredValue`, `useEffectEvent`, `createRoot`,
and similar) confined to `references/legacy-constraints.md`, where they are
the explicit subject rather than mistaken advice.

```bash
uv run python scripts/check_rules.py references/checklist.md references/saga-patterns.md --min-rules 46
uv run python scripts/check_rules.py references/checklist.md references/saga-patterns.md --json
```

Exit code is `1` when any structural error is found or the rule count falls
below `--min-rules`.

## Development

```bash
uv sync --dev
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

## License

MIT. See `LICENSE`.
