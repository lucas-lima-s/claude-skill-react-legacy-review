# Checklist

This catalog is organized by failure mode, not by file type. Each rule names a
symptom you can actually observe while reviewing a diff, shows the pattern
that causes it and the pattern that avoids it, and states when the pattern is
acceptable anyway. Read `severity.md` for how the five impact values rank and
for the accept-by-context policy referenced below. Read `legacy-constraints.md`
before proposing any hook or API not covered here - several categories below
assume nothing beyond what React 16.14 and Redux-Saga actually ship.

## RL-RENDER

Rules about component identity, render cost and list stability in a
browser-rendered tree with no compiler-assisted memoization.

### RL-RENDER-01 - Never define a component inside another component

**Impact:** bug
**Symptom:** an input loses focus while typing, a transition restarts mid-animation, or a scroll position resets, all on a re-render that changed nothing the user can see.

```jsx
// avoid
function TicketRow({ ticket }) {
  const PriorityBadge = () => <span className="badge">{ticket.priority}</span>
  return (
    <div className="row">
      <PriorityBadge />
      <span>{ticket.subject}</span>
    </div>
  )
}
```

```jsx
// prefer
function PriorityBadge({ priority }) {
  return <span className="badge">{priority}</span>
}

function TicketRow({ ticket }) {
  return (
    <div className="row">
      <PriorityBadge priority={ticket.priority} />
      <span>{ticket.subject}</span>
    </div>
  )
}
```

**Accept when:** never. A new component type on every render is a remount, not a style preference.

### RL-RENDER-02 - Derive values during render instead of syncing them through an effect

**Impact:** bug
**Symptom:** the panel shows the previous ticket's priority for one visible frame after switching tickets, because the effect that copies the prop into state runs a render behind.

```jsx
// avoid
function TicketDetail({ ticket }) {
  const [priority, setPriority] = useState(ticket.priority)
  useEffect(() => {
    setPriority(ticket.priority)
  }, [ticket.priority])
  return <PriorityBadge priority={priority} />
}
```

```jsx
// prefer
function TicketDetail({ ticket }) {
  return <PriorityBadge priority={ticket.priority} />
}
```

**Accept when:** the value must be *editable* independently of the prop after the initial render (a draft field seeded from a prop). Reset it with a `key` on the subtree instead of an effect, and document why the effect exists if a `key` is not practical.

### RL-RENDER-03 - Use the functional updater form when the next state depends on the previous state

**Impact:** bug
**Symptom:** a counter or a running total under-counts when several updates happen close together, because a callback captured the state value from the render it was created in.

```jsx
// avoid
function QueueCounter() {
  const [count, setCount] = useState(0)
  const bump = useCallback(() => setCount(count + 1), [count])
  return <button onClick={bump}>{count}</button>
}
```

```jsx
// prefer
function QueueCounter() {
  const [count, setCount] = useState(0)
  const bump = useCallback(() => setCount(c => c + 1), [])
  return <button onClick={bump}>{count}</button>
}
```

**Accept when:** the update genuinely needs the current props or a value that never changes independently of a render, not the previous state - in that case a plain `setState(newValue)` is already correct and wrapping it in an updater adds nothing.

### RL-RENDER-04 - Pass an initializer function to useState instead of computing eagerly

**Impact:** perf
**Symptom:** building an index of a large row set runs on every render of `ReportCanvas`, even though the result is only needed once, because the argument to `useState` is evaluated on every call regardless of whether React uses it.

```jsx
// avoid
function ReportCanvas({ rows }) {
  const [index, setIndex] = useState(buildIndexFromRows(rows))
  return <Grid index={index} />
}
```

```jsx
// prefer
function ReportCanvas({ rows }) {
  const [index, setIndex] = useState(() => buildIndexFromRows(rows))
  return <Grid index={index} />
}
```

**Accept when:** the computation is already cheap (a literal, a short-circuit, a small object) - wrapping trivial work in a function adds a closure allocation for no measurable benefit.

### RL-RENDER-05 - Hoist non-primitive default props out of the render body

**Impact:** rerender
**Symptom:** a memoized `FilterBar` re-renders on every parent update even though none of the values it displays changed, because its `filters` prop falls back to a new empty object each render.

```jsx
// avoid
function ReportPage({ filters }) {
  return <FilterBar filters={filters || {}} />
}
```

```jsx
// prefer
const EMPTY_FILTERS = {}

function ReportPage({ filters }) {
  return <FilterBar filters={filters || EMPTY_FILTERS} />
}
```

**Accept when:** the child is not memoized and re-renders with its parent regardless - hoisting the constant still costs nothing, but the cost of skipping it is also zero, so it is a low-priority cleanup rather than a defect.

### RL-RENDER-06 - Subscribe to a derived boolean instead of a continuously changing value

**Impact:** rerender
**Symptom:** a badge that only needs to know "is the queue non-empty" re-renders on every single item added to or removed from the queue, because it reads the full count.

```jsx
// avoid
function QueueBadge() {
  const itemCount = useSelector(state => state.queue.items.length)
  return itemCount > 0 ? <Dot /> : null
}
```

```jsx
// prefer
function QueueBadge() {
  const hasItems = useSelector(state => state.queue.items.length > 0)
  return hasItems ? <Dot /> : null
}
```

**Accept when:** the component displays the number itself, not just a derived boolean - then it needs the count and this rule does not apply.

### RL-RENDER-07 - Keep transient values that must not trigger a render in a ref

**Impact:** rerender
**Symptom:** dragging a column divider in `StockTable` re-renders the whole table on every `pointermove`, because each intermediate position is written to state purely to compute a delta on release.

```jsx
// avoid
function ColumnResizer({ onResize }) {
  const [lastX, setLastX] = useState(null)
  const handleMove = event => setLastX(event.clientX)
  const handleUp = event => {
    onResize(event.clientX - lastX)
    setLastX(null)
  }
  return <div onPointerMove={handleMove} onPointerUp={handleUp} />
}
```

```jsx
// prefer
function ColumnResizer({ onResize }) {
  const lastX = useRef(null)
  const handleDown = event => { lastX.current = event.clientX }
  const handleUp = event => { onResize(event.clientX - lastX.current) }
  return <div onPointerDown={handleDown} onPointerUp={handleUp} />
}
```

**Accept when:** the value is also shown in the UI while it changes (a live coordinate readout) - then it must be state, and the rerender is the feature, not the bug.

### RL-RENDER-08 - Do not memoize an expression cheaper than the memoization itself

**Impact:** perf
**Symptom:** a profiler shows `useMemo` overhead (dependency comparison, cache bookkeeping) outweighing the cost of the expression it wraps, for something as small as a string concatenation or a single property lookup.

```jsx
// avoid
function AgentBadge({ agent }) {
  const label = useMemo(() => `${agent.firstName} ${agent.lastName}`, [agent.firstName, agent.lastName])
  return <span>{label}</span>
}
```

```jsx
// prefer
function AgentBadge({ agent }) {
  const label = `${agent.firstName} ${agent.lastName}`
  return <span>{label}</span>
}
```

**Accept when:** the wrapped value is passed as a prop to a memoized child and identity stability (not raw compute cost) is the actual goal - then the memoization is protecting against a re-render downstream, not against the cost of the expression, and it is justified.

### RL-RENDER-09 - Use a stable identity for list keys

**Impact:** bug
**Symptom:** renaming a track in `TrackList` collapses its expanded row back to its default state, because the key was derived from the very field that just changed.

```jsx
// avoid
function TrackList({ tracks }) {
  return tracks.map(track => <TrackRow key={track.title} track={track} />)
}
```

```jsx
// prefer
function TrackList({ tracks }) {
  return tracks.map(track => <TrackRow key={track.id} track={track} />)
}
```

**Accept when:** never for data that has a real, stable identifier. If the data genuinely has no id, generate and persist one at the point of creation rather than deriving a key from mutable content.

### RL-RENDER-10 - Do not key a reorderable list by array index

**Impact:** bug
**Symptom:** dragging a row to a new position in `ExpenseTable` leaves the wrong row's inline edit mode "in place" after the drop, because the index-based key now points at a different item.

```jsx
// avoid
function ExpenseTable({ expenses }) {
  return expenses.map((expense, index) => <ExpenseRow key={index} expense={expense} />)
}
```

```jsx
// prefer
function ExpenseTable({ expenses }) {
  return expenses.map(expense => <ExpenseRow key={expense.id} expense={expense} />)
}
```

**Accept when:** the list is provably static for its entire mounted lifetime - never appended to, removed from, filtered, or reordered. That is rare enough that it should be commented at the call site when relied upon.

## RL-EFFECT

Rules about `useEffect` scope, dependencies and cleanup.

### RL-EFFECT-01 - One effect, one concern

**Impact:** maintainability
**Symptom:** a single effect in `ReportCanvas` fetches report data, opens a websocket subscription and sets `document.title`, so touching the dependency array for one concern risks silently breaking another.

```jsx
// avoid
useEffect(() => {
  fetchReport(reportId).then(setReport)
  const sub = socket.subscribe(reportId, handleUpdate)
  document.title = `Report ${reportId}`
  return () => sub.unsubscribe()
}, [reportId])
```

```jsx
// prefer
useEffect(() => {
  fetchReport(reportId).then(setReport)
}, [reportId])

useEffect(() => {
  const sub = socket.subscribe(reportId, handleUpdate)
  return () => sub.unsubscribe()
}, [reportId])

useEffect(() => {
  document.title = `Report ${reportId}`
}, [reportId])
```

**Accept when:** the concerns are trivial and always change together with no independent failure mode - a one-line effect that both sets a CSS class and a data attribute derived from the same single value is not worth splitting.

### RL-EFFECT-02 - Depend on primitive values, not derived objects

**Impact:** bug
**Symptom:** an effect meant to run only when a date range changes fires on every render, because its dependency is a `{ from, to }` object built fresh in the render body.

```jsx
// avoid
function ReportFilters({ from, to }) {
  const range = { from, to }
  useEffect(() => { loadReport(range) }, [range])
}
```

```jsx
// prefer
function ReportFilters({ from, to }) {
  useEffect(() => { loadReport({ from, to }) }, [from, to])
}
```

**Accept when:** the object is already stable across renders (memoized upstream, or a module-level constant) - then depending on its reference is correct and depending on its fields individually would just be more verbose.

### RL-EFFECT-03 - Every subscription needs a matching cleanup

**Impact:** bug
**Symptom:** navigating away from `TicketList` and back doubles the frequency of a handler firing on the next update, because the previous subscription was never removed.

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

**Accept when:** the subscription target is the module's own top-level singleton that must live for the app's entire lifetime (a global error logger registered once at boot) - never inside a component that mounts and unmounts more than once.

### RL-EFFECT-04 - Guard against setting state after the component has unmounted

**Impact:** bug
**Symptom:** a console warning about updating state on an unmounted component, occasionally followed by a crash when the update reads a ref that a cleanup function already cleared.

```jsx
// avoid
useEffect(() => {
  fetchTicket(id).then(result => setTicket(result))
}, [id])
```

```jsx
// prefer
useEffect(() => {
  let cancelled = false
  fetchTicket(id).then(result => {
    if (!cancelled) setTicket(result)
  })
  return () => { cancelled = true }
}, [id])
```

**Accept when:** the component is provably never unmounted before the async work resolves (a full-page loader that owns the entire app lifetime) - a narrow enough case that it should be called out in a comment rather than assumed silently.

### RL-EFFECT-05 - Use an empty dependency array only for work that truly runs once per mount

**Impact:** bug
**Symptom:** an effect written with `[]` to silence a lint warning reads `ticket.subject` from the closure, so the title bar silently keeps showing the ticket that was open when the component first mounted.

```jsx
// avoid
useEffect(() => {
  document.title = `Ticket: ${ticket.subject}`
}, [])
```

```jsx
// prefer
useEffect(() => {
  document.title = `Ticket: ${ticket.subject}`
}, [ticket.subject])
```

**Accept when:** the effect body reads no prop or state at all, or reads only values that are structurally guaranteed constant for the component's lifetime (an id passed once at creation and never reassigned).

### RL-EFFECT-06 - Do not use an effect to mirror a prop into state

**Impact:** bug
**Symptom:** `ExpenseTable` keeps a `status` field synced from the `expense.status` prop through an effect, so the row shows the previous status for one render after an update arrives.

```jsx
// avoid
function ExpenseRow({ expense }) {
  const [status, setStatus] = useState(expense.status)
  useEffect(() => setStatus(expense.status), [expense.status])
  return <StatusPill status={status} />
}
```

```jsx
// prefer
function ExpenseRow({ expense }) {
  return <StatusPill status={expense.status} />
}
```

**Accept when:** the state must diverge from the prop between updates (a locally-edited draft that starts from the prop but the user can then change) - reset it with a `key` when the identity changes, rather than fighting it with an effect on every change.

### RL-EFFECT-07 - Do not depend on an inline object or array literal

**Impact:** bug
**Symptom:** an effect depending on `[{ id: track.id }]` runs on every render, because the dependency array itself contains a freshly allocated object every time, regardless of whether `track.id` changed.

```jsx
// avoid
useEffect(() => {
  loadTrackMetadata(track.id)
}, [{ id: track.id }])
```

```jsx
// prefer
useEffect(() => {
  loadTrackMetadata(track.id)
}, [track.id])
```

**Accept when:** never. There is no version of this pattern that behaves as intended; it always produces the "runs every render" bug this rule describes.

## RL-STATE

Rules about the shape of the Redux store and what belongs in it.

### RL-STATE-01 - Normalize entity collections by id

**Impact:** bug
**Symptom:** updating one ticket's status requires scanning an array of hundreds of tickets to find and replace it, and two components that each hold their own copy of the same ticket can disagree after only one of them applies an update.

```js
// avoid
const initialState = { tickets: [] }

function reducer(state, action) {
  if (action.type === 'tickets/statusChanged') {
    return {
      tickets: state.tickets.map(t =>
        t.id === action.id ? { ...t, status: action.status } : t
      ),
    }
  }
  return state
}
```

```js
// prefer
const initialState = { tickets: { byId: {}, allIds: [] } }

function reducer(state, action) {
  if (action.type === 'tickets/statusChanged') {
    return {
      tickets: {
        ...state.tickets,
        byId: {
          ...state.tickets.byId,
          [action.id]: { ...state.tickets.byId[action.id], status: action.status },
        },
      },
    }
  }
  return state
}
```

**Accept when:** the collection is small (tens of items, not thousands), never looked up by id on a hot path, and never partially updated - a short, fixed list of dashboard widgets is a reasonable exception.

### RL-STATE-02 - Do not store data that can be derived from other state

**Impact:** maintainability
**Symptom:** `state.openTicketCount` drifts from the real number of open tickets after a bulk-close action forgets to decrement it in one of the several code paths that can close a ticket.

```js
// avoid
const initialState = { tickets: {}, openTicketCount: 0 }
```

```js
// prefer
const initialState = { tickets: {} }

function selectOpenTicketCount(state) {
  return Object.values(state.tickets).filter(t => t.status === 'open').length
}
```

**Accept when:** computing the value is expensive enough to matter on every read (a full aggregate over a very large collection) and the write paths that must keep it in sync are few and centralized - then cache it, but memoize the selector first and reach for a stored aggregate only if profiling shows the selector itself is the bottleneck.

### RL-STATE-03 - Memoize selectors that do non-trivial work

**Impact:** rerender
**Symptom:** a selector that filters and sorts thousands of tickets on every store update returns a new array reference each time, so every connected component re-renders even when the visible list did not actually change.

```js
// avoid
const selectOpenTicketsSortedByAge = state =>
  Object.values(state.tickets.byId)
    .filter(t => t.status === 'open')
    .sort((a, b) => a.createdAt - b.createdAt)
```

```js
// prefer
const selectOpenTicketsSortedByAge = createSelector(
  state => state.tickets.byId,
  byId => Object.values(byId)
    .filter(t => t.status === 'open')
    .sort((a, b) => a.createdAt - b.createdAt)
)
```

**Accept when:** the selector's input state changes on essentially every store update anyway (it reads a field that is rewritten by nearly every action) - memoization would never hit its cache and only adds overhead.

### RL-STATE-04 - Keep the store serializable

**Impact:** bug
**Symptom:** replaying recorded actions to reproduce a reported bug fails silently, because one dispatched action carries a live `File` object that cannot be structured-cloned or written to a log.

```js
// avoid
dispatch({ type: 'attachment/added', payload: fileInput.files[0] })
```

```js
// prefer
const file = fileInput.files[0]
attachmentCache.set(file.name, file)
dispatch({
  type: 'attachment/added',
  payload: { name: file.name, size: file.size, type: file.type },
})
```

**Accept when:** the value is explicitly excluded from any tooling that assumes serializability (time-travel debugging, action replay, persistence) and that exclusion is documented at the point the non-serializable value is dispatched.

### RL-STATE-05 - Do not select store state that is only used inside an event handler

**Impact:** rerender
**Symptom:** `ApprovalBanner` re-renders every time the pending-approvals count changes, even though the count is read only inside an `onClick` handler at the moment the button is pressed.

```jsx
// avoid
function ApprovalBanner() {
  const pendingCount = useSelector(state => state.approvals.pending.length)
  const handleApprove = () => submitApproval(pendingCount)
  return <button onClick={handleApprove}>Approve</button>
}
```

```jsx
// prefer
function ApprovalBanner({ store }) {
  const handleApprove = () => {
    const pendingCount = store.getState().approvals.pending.length
    submitApproval(pendingCount)
  }
  return <button onClick={handleApprove}>Approve</button>
}
```

**Accept when:** the value is also rendered somewhere in the component's own output - then the subscription is needed anyway and reading it once for both purposes is simpler than two separate mechanisms.

### RL-STATE-06 - Give action types a stable, structured name

**Impact:** maintainability
**Symptom:** two unrelated features each dispatch an action literally named `'UPDATE'`; after a rename, a saga's `takeEvery('UPDATE', ...)` starts reacting to the wrong feature's actions with no compile-time warning.

```js
// avoid
dispatch({ type: 'UPDATE', payload: expense })
```

```js
// prefer
dispatch({ type: 'expenses/statusChanged', payload: expense })
```

**Accept when:** the action is truly private to one reducer and one component pair, generated and consumed in the same module, and never matched by string elsewhere - even then, the structured name costs nothing and is recommended as the default.

## RL-BUNDLE

Rules about what ships in the initial download for a browser-rendered app
with no server-side code-splitting help.

### RL-BUNDLE-01 - Import directly from the module that defines the export

**Impact:** bundle
**Symptom:** importing a single icon from a shared `components/index.js` barrel file pulls the entire icon set, and every other component the barrel re-exports, into the chunk that imported it.

```js
// avoid
import { ReceiptIcon } from '../components'
```

```js
// prefer
import ReceiptIcon from '../components/icons/ReceiptIcon'
```

**Accept when:** the bundler is configured with reliable tree-shaking for that specific barrel (verified with a bundle report, not assumed) and the barrel exports only side-effect-free modules - confirm both before relying on it.

### RL-BUNDLE-02 - Split code at the route boundary

**Impact:** bundle
**Symptom:** the initial bundle includes the entire expense-approval workflow even for a user who only ever visits the ticket queue, because both routes are imported eagerly at the top of the router module.

```jsx
// avoid
import ApprovalWorkflow from './ApprovalWorkflow'

const routes = [{ path: '/approvals', component: ApprovalWorkflow }]
```

```jsx
// prefer
const ApprovalWorkflow = React.lazy(() => import('./ApprovalWorkflow'))

const routes = [{
  path: '/approvals',
  component: props => (
    <Suspense fallback={<RouteSkeleton />}>
      <ApprovalWorkflow {...props} />
    </Suspense>
  ),
}]
```

**Accept when:** the route is on the app's critical first-paint path for nearly every user session (the landing screen itself) - splitting it would just move the download earlier without shrinking the total the typical user pays for.

### RL-BUNDLE-03 - Gate a heavy dynamic import behind the feature flag that controls it

**Impact:** bundle
**Symptom:** a large charting library used only by an experimental report is downloaded by every user, including the ones the flag excludes, because the `import()` call fires regardless of the flag and only the rendered output is hidden.

```jsx
// avoid
const HeavyChart = React.lazy(() => import('./HeavyChart'))

function Report({ flags }) {
  return flags.advancedExport ? <HeavyChart /> : null
}
```

```jsx
// prefer
function Report({ flags }) {
  if (!flags.advancedExport) return null
  const HeavyChart = React.lazy(() => import('./HeavyChart'))
  return <HeavyChart />
}
```

**Accept when:** the flag is expected to be on for the overwhelming majority of users within one release cycle - a short-lived guard around a chunk everyone will soon load anyway is not worth the added complexity of conditional lazy construction.

### RL-BUNDLE-04 - Keep polyfills out of the main chunk

**Impact:** bundle
**Symptom:** every visitor downloads a `Promise` or `fetch` polyfill in the main bundle, even the large majority on modern browsers that never execute the polyfilled code path.

```js
// avoid
import 'core-js/stable'
import 'whatwg-fetch'
```

```js
// prefer
if (typeof window.fetch === 'undefined') {
  import('whatwg-fetch')
}
```

**Accept when:** the target audience is confirmed (by real usage data, not assumption) to include a large share of browsers that need the polyfill on first load - then the extra request the feature-detection path adds may cost more than shipping it eagerly.

### RL-BUNDLE-05 - Split vendor code deliberately instead of accepting the bundler's default grouping

**Impact:** bundle
**Symptom:** a one-line change to application code invalidates a vendor chunk that also bundles a large, rarely-changing charting library, forcing every user to re-download it on the next deploy.

```js
// avoid
// webpack.config.js - default splitChunks with no explicit cache groups
module.exports = { optimization: { splitChunks: { chunks: 'all' } } }
```

```js
// prefer
// webpack.config.js - a dedicated cache group for large, stable dependencies
module.exports = {
  optimization: {
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        charting: {
          test: /[\\/]node_modules[\\/](chart-lib|chart-lib-adapters)[\\/]/,
          name: 'vendor-charting',
          priority: 10,
        },
      },
    },
  },
}
```

**Accept when:** the app is small enough that a single vendor chunk is already smaller than the threshold where cache-busting on every deploy matters to real users - verify with a bundle report before adding configuration complexity to solve a problem that may not exist yet.

## RL-DOM

Rules about direct DOM cost: list size, listener count, layout thrash.

### RL-DOM-01 - Virtualize long lists

**Impact:** perf
**Symptom:** rendering all 5,000 rows of `StockTable` at once makes scrolling visibly stutter, and the initial paint takes seconds on a mid-range device.

```jsx
// avoid
function StockTable({ items }) {
  return (
    <div className="table">
      {items.map(item => <StockRow key={item.sku} item={item} />)}
    </div>
  )
}
```

```jsx
// prefer
function StockTable({ items }) {
  return (
    <VirtualList
      itemCount={items.length}
      itemSize={32}
      renderItem={index => <StockRow item={items[index]} />}
    />
  )
}
```

**Accept when:** the list is bounded in practice to a size that renders comfortably (dozens, not thousands) - measure the real maximum before adding a virtualization dependency to a list that will never need it.

### RL-DOM-02 - Mark scroll and touch listeners passive

**Impact:** perf
**Symptom:** the browser reports it must wait for a `touchmove` handler to finish before it can start scrolling, producing visible jank on touch devices.

```js
// avoid
element.addEventListener('touchmove', handleDrag)
```

```js
// prefer
element.addEventListener('touchmove', handleDrag, { passive: true })
```

**Accept when:** the handler must call `preventDefault()` to block the browser's default scroll (a custom drag-to-reorder surface) - a passive listener cannot call `preventDefault`, so this case genuinely needs the non-passive form.

### RL-DOM-03 - Delegate instead of attaching one listener per row

**Impact:** perf
**Symptom:** attaching a `click` listener to each of a thousand `TrackList` rows individually slows down both mount and teardown, and every re-render of a row recreates its closure.

```jsx
// avoid
function TrackList({ tracks, onSelect }) {
  return tracks.map(track => (
    <div key={track.id} onClick={() => onSelect(track.id)}>{track.title}</div>
  ))
}
```

```jsx
// prefer
function TrackList({ tracks, onSelect }) {
  const handleClick = event => {
    const row = event.target.closest('[data-track-id]')
    if (row) onSelect(row.dataset.trackId)
  }
  return (
    <div onClick={handleClick}>
      {tracks.map(track => (
        <div key={track.id} data-track-id={track.id}>{track.title}</div>
      ))}
    </div>
  )
}
```

**Accept when:** the list is short and each row's handler genuinely needs distinct captured state that a shared delegate would have to look up anyway - below roughly a few dozen rows, the per-row closures are not the bottleneck.

### RL-DOM-04 - Use content-visibility for long, mostly static regions

**Impact:** perf
**Symptom:** a page with a long read-only audit log takes noticeably longer to paint, because the browser lays out and paints thousands of off-screen rows before the user scrolls anywhere near them.

```css
// avoid
.audit-row-group {
}
```

```css
// prefer
.audit-row-group {
  content-visibility: auto;
  contain-intrinsic-size: 800px;
}
```

**Accept when:** the region's rows have wildly varying heights that make the intrinsic-size estimate unreliable enough to cause visible scrollbar jumps - measure the jump before adopting this rule for that region, and consider virtualization instead.

### RL-DOM-05 - Batch DOM writes to avoid layout thrash

**Impact:** perf
**Symptom:** resizing a panel of `MetricCard` elements reads `offsetWidth` from one card and immediately writes a new style to the next, forcing the browser to recompute layout on every iteration of the loop.

```js
// avoid
cards.forEach(card => {
  const width = card.offsetWidth
  card.style.fontSize = width > 200 ? '1.2rem' : '1rem'
})
```

```js
// prefer
const widths = cards.map(card => card.offsetWidth)
cards.forEach((card, i) => {
  card.style.fontSize = widths[i] > 200 ? '1.2rem' : '1rem'
})
```

**Accept when:** the loop runs over a small, fixed number of elements (three or four cards) where a single forced layout is not measurable - the rule earns its keep on loops over dozens of elements or more.

## RL-JS

Rules about plain JavaScript cost inside a hot render or a large data pass, independent of React.

### RL-JS-01 - Use a Set or Map for repeated membership checks

**Impact:** perf
**Symptom:** checking whether a ticket id is already selected against a plain array, inside a filter over ten thousand tickets, turns a linear scan into a quadratic one for the whole pass.

```js
// avoid
const visibleTickets = tickets.filter(ticket => !selectedIds.includes(ticket.id))
```

```js
// prefer
const selectedIdSet = new Set(selectedIds)
const visibleTickets = tickets.filter(ticket => !selectedIdSet.has(ticket.id))
```

**Accept when:** the membership list has only a handful of entries (single digits) - the overhead of constructing a `Set` can exceed the cost of a short linear scan.

### RL-JS-02 - Build an index before looping instead of scanning repeatedly

**Impact:** perf
**Symptom:** matching each of two thousand expense rows to its approver by scanning the full approver list every time turns a report render into a multi-second operation.

```js
// avoid
const rows = expenses.map(expense => ({
  ...expense,
  approverName: approvers.find(a => a.id === expense.approverId)?.name,
}))
```

```js
// prefer
const approverById = new Map(approvers.map(a => [a.id, a]))
const rows = expenses.map(expense => ({
  ...expense,
  approverName: approverById.get(expense.approverId)?.name,
}))
```

**Accept when:** either list is small enough that the total comparisons stay in the low hundreds - building an index has its own allocation cost that a short scan does not need to pay back.

### RL-JS-03 - Hoist regular expressions out of loops

**Impact:** perf
**Symptom:** constructing a new `RegExp` from a dynamic pattern on every iteration of a filter over thousands of log lines dominates the render time of a report page.

```js
// avoid
function filterByKeyword(lines, keyword) {
  return lines.filter(line => new RegExp(keyword, 'i').test(line))
}
```

```js
// prefer
function filterByKeyword(lines, keyword) {
  const pattern = new RegExp(keyword, 'i')
  return lines.filter(line => pattern.test(line))
}
```

**Accept when:** the pattern itself changes on every call with no loop around it (a single one-off match) - there is no repeated construction to hoist.

### RL-JS-04 - Prefer a single pass over chained filter and map on a profiler-flagged hot path

**Impact:** perf
**Symptom:** `tickets.filter(isOpen).map(toRow)` over fifty thousand tickets allocates and walks two intermediate arrays where a single loop would walk the data once, and a profiler has already flagged this exact call as the largest frame in a slow render.

```js
// avoid
const rows = tickets.filter(isOpen).map(toRow)
```

```js
// prefer
const rows = []
for (const ticket of tickets) {
  if (isOpen(ticket)) rows.push(toRow(ticket))
}
```

**Accept when:** the collection is small or the code path is not on a measured hot path - the chained form reads better and the two-pass cost is invisible below the size where a profiler would ever flag it. Do not apply this rule speculatively; apply it where a measurement justified it.

### RL-JS-05 - Cache a deep property access read repeatedly in a loop

**Impact:** perf
**Symptom:** reading `ticket.metadata.customer.account.tier` inside every comparison of a sort over thousands of tickets re-walks the same four-level chain on every single comparison.

```js
// avoid
tickets.sort((a, b) =>
  a.metadata.customer.account.tier.localeCompare(b.metadata.customer.account.tier)
)
```

```js
// prefer
const tierByTicket = new Map(tickets.map(t => [t, t.metadata.customer.account.tier]))
tickets.sort((a, b) => tierByTicket.get(a).localeCompare(tierByTicket.get(b)))
```

**Accept when:** the collection is small enough, or the sort runs rarely enough, that the repeated chain never shows up in a profile - most sorts over a screen's worth of rows fall into this category and do not need the extra map.

## RL-COMPAT

Rules about relying on an API this React version does not have. Read
`legacy-constraints.md` first for the full capability matrix; these entries
cover the compatibility mistakes a diff review catches most often.

### RL-COMPAT-01 - There is no useId in React 16.14

**Impact:** bug
**Symptom:** an accessibility review flags a form whose label `htmlFor` and input `id` are hard-coded strings that collide whenever the same form component renders twice on one page.

```jsx
// avoid
function LabeledInput({ label }) {
  return (
    <>
      <label htmlFor="field-name">{label}</label>
      <input id="field-name" />
    </>
  )
}
```

```jsx
// prefer
let idCounter = 0

function LabeledInput({ label }) {
  const idRef = useRef(null)
  if (idRef.current === null) idRef.current = `field-${idCounter++}`
  return (
    <>
      <label htmlFor={idRef.current}>{label}</label>
      <input id={idRef.current} />
    </>
  )
}
```

**Accept when:** the parent already controls a unique, stable id for this exact purpose and can pass it down as a prop - then generating a second one locally is redundant.

### RL-COMPAT-02 - There is no useSyncExternalStore in React 16.14

**Impact:** bug
**Symptom:** a component reading from a non-Redux external store (a WebSocket client's in-memory cache) shows a stale value for one extra render after the store updates, because there is no built-in hook for a safe, tear-free subscription.

```jsx
// avoid
function ConnectionStatus() {
  return <span>{websocketClient.getSnapshot().status}</span>
}
```

```jsx
// prefer
function ConnectionStatus() {
  const [status, setStatus] = useState(() => websocketClient.getSnapshot().status)
  useEffect(() => {
    const unsubscribe = websocketClient.subscribe(() => {
      setStatus(websocketClient.getSnapshot().status)
    })
    return unsubscribe
  }, [])
  return <span>{status}</span>
}
```

**Accept when:** the external value only needs to be read once, at mount, and never changes for the component's lifetime - then a plain `useState` initializer is enough and no subscription is needed at all.

### RL-COMPAT-03 - There is no built-in way to keep a hidden subtree alive in React 16.14

**Impact:** bug
**Symptom:** switching a tab away from and back to a heavy `ReportCanvas` remounts it from scratch, losing scroll position and in-progress local state, because conditional rendering unmounts the previous tree entirely.

```jsx
// avoid
function TabbedReports({ activeTab }) {
  return activeTab === 'canvas' ? <ReportCanvas /> : null
}
```

```jsx
// prefer
function TabbedReports({ activeTab }) {
  return (
    <div style={{ display: activeTab === 'canvas' ? 'block' : 'none' }}>
      <ReportCanvas />
    </div>
  )
}
```

**Accept when:** the state genuinely does not need to survive a tab switch - then unmounting on hide is simpler and frees the memory and DOM nodes the hidden alternative would keep alive.

### RL-COMPAT-04 - There is no framework-level resource-preload hint in React 16.14

**Impact:** perf
**Symptom:** a report page requests a large data file only after the component that needs it has already rendered, adding a visible delay, because nothing hints the browser to start that request earlier.

```jsx
// avoid
function ReportPage({ reportId }) {
  const [data, setData] = useState(null)
  useEffect(() => { fetchReportData(reportId).then(setData) }, [reportId])
  return data ? <ReportCanvas data={data} /> : <Skeleton />
}
```

```jsx
// prefer
function loadReportRoute(reportId) {
  const promise = fetchReportData(reportId)
  return { reportId, promise }
}

function ReportPage({ reportId, promise }) {
  const [data, setData] = useState(null)
  useEffect(() => { promise.then(setData) }, [promise])
  return data ? <ReportCanvas data={data} /> : <Skeleton />
}
```

**Accept when:** the route is not known ahead of the component mounting (fully dynamic, in-browser navigation with no router-level hook to start the fetch earlier) - there is nothing to preload against in that case.

### RL-COMPAT-05 - Automatic batching only applies inside React event handlers

**Impact:** bug
**Symptom:** two `setState` calls inside a `setTimeout` callback, or inside a raw WebSocket `onmessage` handler, each trigger their own render, producing a visible flash of an intermediate state a handler-scoped update would never show.

```jsx
// avoid
websocket.onmessage = event => {
  const payload = JSON.parse(event.data)
  setStatus(payload.status)
  setLastSeen(payload.timestamp)
}
```

```jsx
// prefer
websocket.onmessage = event => {
  const payload = JSON.parse(event.data)
  setState(prev => ({ ...prev, status: payload.status, lastSeen: payload.timestamp }))
}
```

**Accept when:** the two updates are independent enough that an intermediate render between them is harmless (unrelated pieces of UI, no shared invariant) - then the extra render is a performance question, not a correctness one.

### RL-COMPAT-06 - Error boundaries must be class components; lazy loading needs no version upgrade

**Impact:** bug
**Symptom:** a review comment suggests rewriting an error boundary as a function component with a hook, which cannot work because catching render errors still requires the class lifecycle; separately, a team defers route-level code splitting "until the framework supports it," when the mechanism has already been available for years.

```jsx
// avoid
function ReportBoundary({ children }) {
  const [error, setError] = useState(null)
  if (error) return <ErrorMessage error={error} />
  return children
}
```

```jsx
// prefer
class ReportBoundary extends React.Component {
  state = { error: null }
  static getDerivedStateFromError(error) {
    return { error }
  }
  componentDidCatch(error, info) {
    logReportError(error, info)
  }
  render() {
    if (this.state.error) return <ErrorMessage error={this.state.error} />
    return this.props.children
  }
}
```

**Accept when:** never for the error-boundary half of this rule - a function component structurally cannot implement `getDerivedStateFromError` or `componentDidCatch`. The lazy-loading half has no valid exception either: `React.lazy` needs no version beyond what this codebase already runs.
