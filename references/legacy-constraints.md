# Legacy constraints: what React 16.14 does not have

Most React advice published today assumes React 18's concurrent renderer, or
assumes the code runs inside a server framework with its own rendering
model. Neither assumption holds for a browser-rendered React 16.14 app. This
page is the capability matrix a reviewer checks before accepting any
suggestion that names an API this version does not ship, or that carries an
assumption from a different rendering model.

Every row states the API or assumption, the React version it actually
requires, and what a React 16.14 codebase does instead.

## Concurrent-rendering APIs

| API / hook | Introduced in | What React 16.14 has instead |
|---|---|---|
| `useTransition` | 18.0 | No priority-marked updates exist. Every `setState` call is treated the same; there is no way to tell React "this update can be interrupted." Defer expensive work explicitly with `setTimeout` or a work-splitting utility instead of marking it low priority. |
| `useDeferredValue` | 18.0 | No built-in mechanism to let a fast update (typing) render ahead of a slow one (a filtered list) derived from it. Debounce or throttle the expensive derivation by hand at the call site instead. |
| `useId` | 18.0 | See `RL-COMPAT-01` in `checklist.md` for the substitute: a ref-backed counter or an id passed down explicitly. |
| `useSyncExternalStore` | 18.0 | See `RL-COMPAT-02` in `checklist.md` for the substitute: a manual `useEffect` subscription paired with `useState`. |
| `useEffectEvent` | 19.2 (stable) | There is no way to read the latest props or state inside an effect without adding them to the dependency array or capturing them in a ref updated on every render. Use the ref-capture pattern explicitly rather than assuming an effect can see "the latest" value implicitly. |
| `<Activity>` | 19.2 (stable) | See `RL-COMPAT-03` in `checklist.md` for the substitute: keep the subtree mounted and toggle CSS visibility instead of unmounting and remounting it. |

## Rendering entry point and resource hints

| API | Introduced in | What React 16.14 has instead |
|---|---|---|
| `createRoot` | 18.0 (the `react-dom/client` root API) | The entry point is `ReactDOM.render(element, container)`. There is no root object to hold onto for a later `unmount()` call in the new form; `ReactDOM.unmountComponentAtNode(container)` is the 16.14 equivalent. |
| `ReactDOM.preload` / `ReactDOM.preinit` | 19.0 | See `RL-COMPAT-04` in `checklist.md` for the substitute: an explicit `<link rel="preload">` tag managed by the app's own head-tag utility, or an imperative fetch kicked off as soon as the route is known. |

## Batching scope

Automatic batching - every `setState` call inside the same tick collapsing
into a single render, regardless of where the tick started - is an 18.0
change. In React 16.14, batching only happens inside a React event handler.
A `setState` call made from a `setTimeout` callback, a native DOM event
listener registered outside React, or a resolved promise's `.then` callback
each triggers its own render immediately. Two such calls in a row produce two
renders and a visible intermediate state, not one. See `RL-COMPAT-05` in
`checklist.md` for the fix: combine the updates into one call, or route them
through the library's own batching utility when it is available.

## Error boundaries and code splitting

Error boundaries require class-component lifecycle methods
(`static getDerivedStateFromError` and `componentDidCatch`) in every React
version through 16.14; there is still no hook-based equivalent as of that
release. `React.lazy` has been available since 16.6 and is the supported
code-splitting mechanism for this codebase - it needs no version upgrade to
adopt. See `RL-COMPAT-06` in `checklist.md`.

## Why so much current advice does not apply

A large share of React material published in the last few years assumes one
of two things this codebase does not have: React 18's concurrent renderer
(the APIs above), or a server framework with Server Components, React
Server Components (RSC), and an app-router-style file convention that
decides what runs on the server versus in the browser. None of that exists
here - this is a browser-rendered, webpack-bundled, statically hosted
single page app with no server rendering step at all. When a suggestion
mentions a
Server Component, an RSC boundary, an app router file convention, or an
import from a `next/`-style framework package, it does not apply to this
codebase regardless of how current or well-regarded the advice is elsewhere.
Check every such suggestion against this page, and against the two tables
above, before accepting it.
