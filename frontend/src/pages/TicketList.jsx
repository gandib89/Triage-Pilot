import { useState, useEffect } from 'react'

const API_BASE = '/api'

function TicketList() {
    const [tickets, setTickets] = useState([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        fetch(`${API_BASE}/tickets/`)
            .then(res => {
                if (!res.ok) throw new Error(`Server error: ${res.status}`)
                return res.json()
            })
            .then(data => setTickets(data))
            .catch(err => setError(err.message))
            .finally(() => setIsLoading(false))
    }, [])

    if (isLoading) return <p>Loading tickets...</p>
    if (error) return <p>Error: {error}</p>

    return (
        <main>
            <h1>Tickets</h1>
            {tickets.length === 0 ? (
                <p>No tickets yet.</p>
            ) : (
                <ul>
                    {tickets.map(ticket => (
                        <li key={ticket.id}>
                            <strong>{ticket.subject}</strong> — {ticket.status}
                        </li>
                    ))}
                </ul>
            )}
        </main>
    )
}

export default TicketList
