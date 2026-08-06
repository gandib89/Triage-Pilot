import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../api'
import './TriageQueue.css'

function TriageQueue() {
    const [decisions, setDecisions] = useState([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        api.get('/decisions/?status=pending')
            .then(res => setDecisions(res.data.results || res.data))
            .catch(err => setError(err.message))
            .finally(() => setIsLoading(false))
    }, [])

    if (isLoading) return <p>Loading triage queue...</p>
    if (error) return <p>Error: {error}</p>

    return (
        <main className="triage-queue">
            <h1>Triage Queue</h1>
            {decisions.length === 0 ? (
                <p>No pending decisions.</p>
            ) : (
                <ul className="queue-list">
                    {decisions.map(decision => (
                        <li key={decision.id} className="queue-item">
                            <Link to={`/triage/${decision.id}`}>
                                <div className="queue-item-header">
                                    <strong>{decision.ticket.subject}</strong>
                                    <span className={`badge urgency-${decision.ticket.urgency || 'none'}`}>
                                        {decision.ticket.urgency || 'unset'}
                                    </span>
                                    <span className="badge category">
                                        {decision.ticket.category || 'uncategorized'}
                                    </span>
                                </div>
                                <p className="queue-item-preview">{decision.proposed_action}</p>
                            </Link>
                        </li>
                    ))}
                </ul>
            )}
        </main>
    )
}

export default TriageQueue
