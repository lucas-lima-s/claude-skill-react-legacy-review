const initialState = {
  tickets: { byId: {}, allIds: [] },
}

function ticketsReducer(state = initialState, action) {
  switch (action.type) {
    case "tickets/loaded": {
      const byId = {}
      const allIds = []
      for (const ticket of action.payload) {
        byId[ticket.id] = ticket
        allIds.push(ticket.id)
      }
      return { tickets: { byId, allIds } }
    }
    case "tickets/statusChanged": {
      const existing = state.tickets.byId[action.payload.id]
      if (!existing) return state
      return {
        tickets: {
          ...state.tickets,
          byId: {
            ...state.tickets.byId,
            [action.payload.id]: { ...existing, status: action.payload.status },
          },
        },
      }
    }
    default:
      return state
  }
}

function selectAllTickets(state) {
  return state.tickets.allIds.map(id => state.tickets.byId[id])
}

function selectTicketById(state, id) {
  return state.tickets.byId[id]
}

export { ticketsReducer, selectAllTickets, selectTicketById }
