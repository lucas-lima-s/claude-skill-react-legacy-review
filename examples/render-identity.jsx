import React, { useCallback, useRef, useState } from "react"

function PriorityBadge({ priority }) {
  return <span className={`badge badge-${priority}`}>{priority}</span>
}

function TicketRow({ ticket, onSelect }) {
  const lastPointerX = useRef(null)

  const handlePointerDown = event => {
    lastPointerX.current = event.clientX
  }

  const handlePointerUp = event => {
    const delta = event.clientX - lastPointerX.current
    if (Math.abs(delta) < 4) {
      onSelect(ticket.id)
    }
  }

  return (
    <div
      className="ticket-row"
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerUp}
    >
      <PriorityBadge priority={ticket.priority} />
      <span>{ticket.subject}</span>
    </div>
  )
}

export function TicketQueue({ tickets }) {
  const [selectedCount, setSelectedCount] = useState(0)

  const handleSelect = useCallback(() => {
    setSelectedCount(count => count + 1)
  }, [])

  return (
    <div className="ticket-queue">
      <div className="ticket-queue-header">Selected: {selectedCount}</div>
      {tickets.map(ticket => (
        <TicketRow key={ticket.id} ticket={ticket} onSelect={handleSelect} />
      ))}
    </div>
  )
}
