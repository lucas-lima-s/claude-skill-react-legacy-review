import { all, call, cancelled, fork, put, take, takeLatest } from "redux-saga/effects"

function* loadDashboardSaga() {
  const [tickets, agents, metrics] = yield all([
    call(fetchTickets),
    call(fetchAgents),
    call(fetchMetrics),
  ])
  yield put(dashboardLoaded({ tickets, agents, metrics }))
}

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

function* watchDragSaga() {
  const channel = yield call(createDragChannel, buffers.sliding(1))
  while (true) {
    const position = yield take(channel)
    yield call(applyDragSaga, position)
  }
}

export default function* rootSaga() {
  yield all([
    call(loadDashboardSaga),
    takeLatest("seat/reserveRequested", reserveSeatSaga),
    fork(watchDragSaga),
  ])
}
