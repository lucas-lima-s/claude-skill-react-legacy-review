# Saga patterns

Redux-Saga review rules. A saga bug rarely shows up as a stack trace; it shows
up as a race, a stuck loading spinner, or a resource that never gets
released. These rules cover the concurrency and lifecycle mistakes that are
specific to generator-based effects and have no counterpart in plain
component review.

## RL-SAGA

### RL-SAGA-01 - Run independent work with all or fork, not sequential yield call

**Impact:** perf
**Symptom:** loading a dashboard's three independent widgets takes the sum of three network round trips instead of the slowest one, because each `yield call(...)` waits for the previous one to resolve before starting the next.

```js
// avoid
function* loadDashboardSaga() {
  const tickets = yield call(fetchTickets)
  const agents = yield call(fetchAgents)
  const metrics = yield call(fetchMetrics)
  yield put(dashboardLoaded({ tickets, agents, metrics }))
}
```

```js
// prefer
function* loadDashboardSaga() {
  const [tickets, agents, metrics] = yield all([
    call(fetchTickets),
    call(fetchAgents),
    call(fetchMetrics),
  ])
  yield put(dashboardLoaded({ tickets, agents, metrics }))
}
```

**Accept when:** a later call genuinely needs the result of an earlier one (a real data dependency, such as fetching a ticket before its comments). Sequential `yield call` is then correct, and forcing it into `all` would just pass `undefined` where a real value belongs.

### RL-SAGA-02 - Choose takeLatest or takeEvery deliberately, and know what cancellation implies

**Impact:** bug
**Symptom:** a search-as-you-type saga built with `takeEvery` lets an outdated response overwrite a newer one, so the result list flickers back to a stale set after the user has already typed further.

```js
// avoid
function* watchSearchSaga() {
  yield takeEvery('search/queryChanged', searchSaga)
}
```

```js
// prefer
function* watchSearchSaga() {
  yield takeLatest('search/queryChanged', searchSaga)
}
```

**Accept when:** every occurrence of the action must run to completion independently of the others - a bulk "export this row" action fired once per row in a batch, where dropping any one of them would silently lose work. `takeEvery` is correct there and `takeLatest` would discard requests the caller expects to complete.

### RL-SAGA-03 - Clean up cancelled work with finally and cancelled()

**Impact:** bug
**Symptom:** a `takeLatest` saga that reserves a temporary lock on a seat never releases it when a newer action cancels the in-flight instance, leaving the seat locked until a timeout elsewhere clears it.

```js
// avoid
function* reserveSeatSaga(action) {
  yield call(acquireLock, action.seatId)
  const result = yield call(confirmSeat, action.seatId)
  yield put(seatConfirmed(result))
  yield call(releaseLock, action.seatId)
}
```

```js
// prefer
function* reserveSeatSaga(action) {
  try {
    yield call(acquireLock, action.seatId)
    const result = yield call(confirmSeat, action.seatId)
    yield put(seatConfirmed(result))
  } finally {
    yield call(releaseLock, action.seatId)
    if (yield cancelled()) {
      yield call(logCancelledReservation, action.seatId)
    }
  }
}
```

**Accept when:** the resource has its own independent expiry that makes a leaked lock harmless within an acceptable window (a soft reservation that times out server-side in under a second) - document the timeout at the acquisition call site if this is relied upon instead of explicit cleanup.

### RL-SAGA-04 - Do not select inside a tight loop

**Impact:** perf
**Symptom:** a saga processing a batch of five hundred queued messages calls `yield select(getFeatureFlags)` once per message instead of once for the whole batch, adding hundreds of redundant store reads to a single batch's processing time.

```js
// avoid
function* processBatchSaga(action) {
  for (const message of action.batch) {
    const flags = yield select(getFeatureFlags)
    yield call(handleMessage, message, flags)
  }
}
```

```js
// prefer
function* processBatchSaga(action) {
  const flags = yield select(getFeatureFlags)
  for (const message of action.batch) {
    yield call(handleMessage, message, flags)
  }
}
```

**Accept when:** the value read can genuinely change mid-loop in a way each iteration must observe (a cancellation flag another saga can flip while this one runs) - then re-reading it each iteration is required, not redundant.

### RL-SAGA-05 - Keep business rules in sagas, not in the components that dispatch to them

**Impact:** maintainability
**Symptom:** the rule "an expense over a threshold requires a second approver" is implemented inline inside one button's click handler, so a second entry point that dispatches the same action - a keyboard shortcut, a bulk-action bar - bypasses the rule entirely.

```jsx
// avoid
function ApprovalButton({ expense }) {
  const handleClick = () => {
    if (expense.amount > 5000) {
      dispatch(escalationRequested(expense.id))
    } else {
      dispatch(approvalRequested(expense.id))
    }
  }
  return <button onClick={handleClick}>Approve</button>
}
```

```jsx
// prefer
function ApprovalButton({ expense }) {
  return <button onClick={() => dispatch(approvalRequested(expense.id))}>Approve</button>
}
```

```js
// prefer (in the saga)
function* approvalRequestedSaga(action) {
  const expense = yield select(selectExpenseById(action.expenseId))
  if (expense.amount > 5000) {
    yield put(escalationRequested(expense.id))
  } else {
    yield call(submitApproval, expense.id)
  }
}
```

**Accept when:** the decision is purely a display concern with no side effect of its own (which label a button shows) - then it can live in the component, because there is no second entry point that could bypass a rendering choice.

### RL-SAGA-06 - Batch related updates instead of causing a put storm

**Impact:** rerender
**Symptom:** processing a batch of two hundred incoming websocket messages dispatches two hundred separate `put` calls, each triggering a render of every connected component before the next message is even processed.

```js
// avoid
function* handleIncomingBatchSaga(action) {
  for (const message of action.batch) {
    yield put(messageReceived(message))
  }
}
```

```js
// prefer
function* handleIncomingBatchSaga(action) {
  yield put(messagesReceived(action.batch))
}
```

**Accept when:** each item in the batch must reach the store as soon as it is individually ready, with no acceptable delay for the rest of the batch (a live progress indicator that must tick per item) - the rerender cost is then the feature, not a defect.

### RL-SAGA-07 - Give each long-running saga its own error boundary so one failure does not kill the root

**Impact:** bug
**Symptom:** an unhandled rejection inside one feature's saga - a malformed response from a rarely used endpoint - stops the saga middleware entirely, silently disabling every other feature's sagas for the rest of the session.

```js
// avoid
export default function* rootSaga() {
  yield all([
    call(ticketsSaga),
    call(approvalsSaga),
    call(analyticsSaga),
  ])
}
```

```js
// prefer
function* withErrorLogging(saga) {
  try {
    yield call(saga)
  } catch (error) {
    yield call(logSagaError, saga.name, error)
  }
}

export default function* rootSaga() {
  yield all([
    call(withErrorLogging, ticketsSaga),
    call(withErrorLogging, approvalsSaga),
    call(withErrorLogging, analyticsSaga),
  ])
}
```

**Accept when:** a failure in that specific saga is meant to be fatal to the whole app by design (a saga that verifies an auth token is still valid, where continuing with the other sagas would be actively wrong) - state that intent at the call site instead of relying on the default behavior by omission.

### RL-SAGA-08 - Use a channel for a producer that can burst faster than the consumer processes

**Impact:** bug
**Symptom:** a saga listening for raw pointer-drag events with `takeEvery` falls behind during a fast drag, processing a growing backlog of stale positions well after the user has already released the mouse.

```js
// avoid
function* watchDragSaga() {
  yield takeEvery('drag/pointerMoved', applyDragSaga)
}
```

```js
// prefer
function* watchDragSaga() {
  const channel = yield call(createDragChannel, buffers.sliding(1))
  while (true) {
    const position = yield take(channel)
    yield call(applyDragSaga, position)
  }
}
```

**Accept when:** the producer cannot realistically outpace the consumer (a burst of at most a handful of events per user action, such as form field changes) - a channel with an explicit buffer policy adds ceremony that a plain `takeLatest` or `takeEvery` already handles correctly at that volume.

### RL-SAGA-09 - Never block the root saga on a long-running call

**Impact:** bug
**Symptom:** a feature saga that awaits a slow long-polling request directly under the root saga's `all([...])` list delays the app from ever finishing its startup saga chain, because `all` waits for every entry to settle before the surrounding generator continues.

```js
// avoid
export default function* rootSaga() {
  yield all([
    call(startupSaga),
    call(longPollingSaga),
  ])
}
```

```js
// prefer
export default function* rootSaga() {
  yield all([
    call(startupSaga),
    fork(longPollingSaga),
  ])
}
```

**Accept when:** the long-running task genuinely must complete (or fail) before the rest of the app is allowed to proceed - a startup health check that blocks the UI until it resolves is a legitimate use of `call`, and the fix here is to shorten or time-box that call, not to `fork` it away.
