import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import api from '../api'

function TicketDetail() {
    const { id } = useParams()
    const [ticket, setTicket] = useState(null)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        api.get(`/tickets/${id}/`)
            .then(res => setTicket(res.data))
            .catch(err => setError(err.message))
            .finally(() => setIsLoading(false))
    }, [id])

    if (isLoading) return <p>Loading...</p>
    if (error) return <p>Error: {error}</p>

    return (
        <main>
            <h1>{ticket.subject}</h1>
            <p><strong>Status:</strong> {ticket.status}</p>
            <p><strong>Category:</strong> {ticket.category}</p>
            <p><strong>Urgency:</strong> {ticket.urgency}</p>
            <p><strong>Body:</strong> {ticket.body}</p>
            <p><strong>Created:</strong> {ticket.created_at}</p>
        </main>
    )
}

export default TicketDetail
