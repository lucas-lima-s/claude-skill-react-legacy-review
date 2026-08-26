---
name: react-legacy-review
description: Review React 16 plus Redux-Saga code in a legacy browser-rendered app against a checklist organized by failure mode - render identity, effect dependencies, saga concurrency, store shape, bundle size, DOM cost - and flag advice that silently assumes React 18 or a server framework. Use when reviewing or editing React components, containers, sagas, selectors or reducers in an older codebase. Triggers on "review this React component", "React 16 review", "redux saga review", "legacy frontend review", "revisa esse componente React", "checklist React legado".
---

## How to use this skill

1. Identify which categories the diff touches, then read only the matching
   sections of `references/checklist.md` and `references/saga-patterns.md` -
   there is no need to read the whole catalog for a small diff.
2. Apply every rule whose category matches something the diff changes.
   Report each violation as a finding using the output contract below.
3. Before proposing any hook, component, or API that looks like current
   React advice, check it against `references/legacy-constraints.md`. Most
   material published in the last few years assumes React 18's concurrent
   renderer or a server framework; neither exists in this codebase.
4. When a finding should be deferred rather than fixed inline, record it as
   accepted-by-context using the policy and the one-line justification
   format in `references/severity.md`, not by silently skipping it.

## Categories

- **RL-RENDER** - component identity, render cost, and list key stability.
- **RL-EFFECT** - effect scope, dependency correctness, and cleanup.
- **RL-SAGA** - generator concurrency, cancellation, and saga lifecycle.
- **RL-STATE** - Redux store shape, selector cost, and serializability.
- **RL-BUNDLE** - what ships in the initial download.
- **RL-DOM** - direct DOM cost: list size, listener count, layout thrash.
- **RL-JS** - plain JavaScript cost on a hot path, independent of React.
- **RL-COMPAT** - APIs and assumptions this React version does not support.

## Output contract

Report each finding as:

- **Rule:** the rule id, for example `RL-EFFECT-03`.
- **Location:** `file:line`.
- **Symptom:** what a user or another developer would actually observe.
- **Fix:** the concrete change, not a restatement of the rule.
- **Impact:** one of `bug`, `rerender`, `bundle`, `perf`, `maintainability`,
  taken from the rule itself.

When a finding is accepted-by-context instead of fixed, report it the same
way and add a **Reason** line naming which of the three accept-by-context
conditions in `references/severity.md` applies.

## Boundary

This skill covers React component and Redux-Saga review only. It does not
cover:

- End-to-end or integration test review.
- General JavaScript style unrelated to a hot path (formatting, naming
  conventions outside `RL-STATE-06`).
- Build tooling configuration beyond the bundle size rules in `RL-BUNDLE`.

## The React-version warning

Most React guidance available today - blog posts, official examples, model
training data - defaults to describing React 18 or newer, or a server
framework's rendering model. Before accepting a suggestion that mentions a
hook, a component, or a rendering primitive not already in this codebase,
check it against the capability matrix in `references/legacy-constraints.md`.
If the suggestion depends on something that matrix marks as unavailable,
it does not apply here, regardless of how current or well-regarded the
advice is elsewhere.
