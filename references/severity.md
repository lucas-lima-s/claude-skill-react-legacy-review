# Severity and the accept-when policy

Every rule in `checklist.md` and `saga-patterns.md` carries an **Impact**
value from a fixed set of five. This page defines each value, how to rank
findings when a diff triggers more than one rule, and the policy for
recording a finding as accepted rather than fixed.

## The five impact values

**bug** - the code produces a wrong result, a wrong visual state, a leak, or
a race under conditions that will occur in normal use, not only under an
edge case a user is unlikely to hit. This is the highest-priority value:
a finding tagged `bug` blocks a review by default.

**rerender** - the code is correct but re-renders more than it needs to.
The user sees no wrong result, but the component tree does more work than
the data change justifies. Worth flagging in any component on a path a
profiler has flagged, optional elsewhere.

**bundle** - the code ships more bytes to the browser than the feature
requires: an eager import that could be lazy, a barrel that defeats
tree-shaking, a polyfill everyone downloads for a browser gap only some
users have. Flag it when it affects the initial route; treat it as lower
priority for a route most users never visit.

**perf** - a cost outside of rendering itself: a DOM operation, a data
transformation, a saga doing more store reads or generator steps than the
data justifies. Rank it by measured or clearly evident cost, not by how
unusual the pattern looks - an O(n²) scan over a ten-item list is not worth
a finding; the same scan over ten thousand items is.

**maintainability** - the code works and performs acceptably today, but its
structure makes the next correct change harder or riskier than it needs to
be: a business rule duplicated across two dispatch sites, an effect mixing
three unrelated concerns, a magic action-type string. Lowest priority of
the five for a single review, but worth naming so it does not accumulate
silently across many reviews.

## Ranking findings in one diff

When a diff triggers several rules, order findings `bug` first, then
`rerender` and `perf` together (rank by evidence: a measured slowdown or an
obviously large collection outranks a theoretical one), then `bundle`, then
`maintainability` last. A single `bug` finding is worth blocking a merge
over; a page full of `maintainability` findings on code the diff barely
touches is worth a comment, not a block.

## The accept-when policy for legacy code

Every rule in this catalog states its own **Accept when** clause: the
specific condition under which the pattern the rule warns about is
actually the right call. Read that clause first - most exceptions belong
there, tied to the technical reason a rule does not apply, not to the fact
that the surrounding code is old.

Beyond a rule's own **Accept when** clause, a finding may additionally be
recorded as **accepted-by-context** - noted rather than fixed inline -
under any of these three conditions, each logged with a one-line
justification next to the finding:

1. **The surrounding module already commits to the older pattern.** A file
   that consistently mirrors props into state through effects, function by
   function, is not the place to fix one instance in isolation as a side
   effect of an unrelated change; flag it once for the module, not once per
   line the diff happens to touch.
2. **The fix would require retesting an area the pull request does not
   touch.** If correcting a `RL-STATE-01` normalization issue means
   updating every reducer and every selector that reads the denormalized
   shape, and the current change has nothing to do with that state slice,
   record the debt instead of expanding the diff's blast radius.
3. **The fix is larger than the change under review.** A one-line bug fix
   is not the place to also split a three-hundred-line component that
   happens to contain the line being fixed.

A finding accepted under any of these three conditions is still a finding:
name the rule id, the reason it is being deferred rather than fixed, and
where the debt now lives, so the next reviewer does not have to
re-discover it from scratch.
