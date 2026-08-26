import React, { useEffect, useState } from "react"

export function ConnectionStatus({ socket }) {
  const [status, setStatus] = useState(() => socket.getStatus())

  useEffect(() => {
    let cancelled = false

    const handleChange = nextStatus => {
      if (!cancelled) setStatus(nextStatus)
    }

    socket.on("status", handleChange)
    return () => {
      cancelled = true
      socket.off("status", handleChange)
    }
  }, [socket])

  return <span className={`status status-${status}`}>{status}</span>
}

export function TicketDetail({ ticketId, fetchTicket }) {
  const [ticket, setTicket] = useState(null)

  useEffect(() => {
    let cancelled = false

    fetchTicket(ticketId).then(result => {
      if (!cancelled) setTicket(result)
    })

    return () => {
      cancelled = true
    }
  }, [ticketId, fetchTicket])

  useEffect(() => {
    if (ticket) {
      document.title = `Ticket: ${ticket.subject}`
    }
  }, [ticket])

  if (!ticket) return <span>Loading...</span>
  return <span>{ticket.subject}</span>
}
