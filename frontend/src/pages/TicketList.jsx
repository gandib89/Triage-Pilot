import { useState, useEffect } from 'react'
import api from '../api'

function TicketList() {
    const [tickets, setTickets] = useState([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        api.get('/tickets/')
            .then(res => setTickets(res.data.results ?? res.data))
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
