import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../api'
import './TriageQueue.css'

function DecisionDetail() {
    const { id } = useParams()
    const navigate = useNavigate()
    const [decision, setDecision] = useState(null)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState(null)
    const [isEditing, setIsEditing] = useState(false)
    const [editedText, setEditedText] = useState('')
    const [isSubmitting, setIsSubmitting] = useState(false)

    useEffect(() => {
        api.get(`/decisions/${id}/`)
            .then(res => {
                setDecision(res.data)
                setEditedText(res.data.proposed_action)
            })
            .catch(err => setError(err.message))
            .finally(() => setIsLoading(false))
    }, [id])

    const submitDecision = async (decisionType) => {
        setIsSubmitting(true)
        setError(null)
        try {
            const payload = { decision: decisionType }
            if (decisionType === 'edited') payload.edited_action = editedText
            await api.post(`/decisions/${id}/decide/`, payload)
            navigate('/triage')
        } catch (err) {
            setError(err.response?.data ? JSON.stringify(err.response.data) : err.message)
        } finally {
            setIsSubmitting(false)
        }
    }

    if (isLoading) return <p>Loading...</p>
    if (error && !decision) return <p>Error: {error}</p>
    if (!decision) return null

    const { ticket } = decision
    const alreadyDecided = Boolean(decision.human_decision)

    return (
        <main className="decision-detail">
            <h1>Review Decision</h1>
            {alreadyDecided && (
                <p className="already-decided">
                    Already decided: <strong>{decision.human_decision}</strong>
                </p>
            )}
            {error && <p className="form-error">Error: {error}</p>}

            <div className="side-by-side">
                <section className="panel">
                    <h2>Ticket</h2>
                    <p><strong>Subject:</strong> {ticket.subject}</p>
                    <p><strong>Category:</strong> {ticket.category || 'uncategorized'}</p>
                    <p><strong>Urgency:</strong> {ticket.urgency || 'unset'}</p>
                    <p><strong>Body:</strong></p>
                    <p className="body-text">{ticket.body}</p>
                </section>

                <section className="panel">
                    <h2>Proposed Action</h2>
                    <p><strong>Agent reasoning:</strong></p>
                    <p className="body-text">{decision.agent_reasoning}</p>

                    <p><strong>Action:</strong></p>
                    {isEditing ? (
                        <textarea
                            className="edit-textarea"
                            value={editedText}
                            onChange={e => setEditedText(e.target.value)}
                            rows={8}
                        />
                    ) : (
                        <p className="body-text">
                            {decision.edited_action || decision.proposed_action}
                        </p>
                    )}

                    <p><strong>Sources cited:</strong></p>
                    {(() => {
                        const sources = Array.isArray(decision.sources_used)
                            ? decision.sources_used
                            : decision.sources_used ? [decision.sources_used] : []
                        return sources.length > 0 ? (
                            <ul className="sources-list">
                                {sources.map((source, i) => (
                                    <li key={i}>{typeof source === 'string' ? source : JSON.stringify(source)}</li>
                                ))}
                            </ul>
                        ) : (
                            <p>No sources cited.</p>
                        )
                    })()}
                </section>
            </div>

            {!alreadyDecided && (
                <div className="decision-controls">
                    {isEditing ? (
                        <>
                            <button disabled={isSubmitting} onClick={() => submitDecision('edited')}>
                                Save Edit &amp; Approve
                            </button>
                            <button disabled={isSubmitting} onClick={() => { setIsEditing(false); setEditedText(decision.proposed_action) }}>
                                Cancel
                            </button>
                        </>
                    ) : (
                        <>
                            <button disabled={isSubmitting} onClick={() => submitDecision('approved')}>
                                Approve
                            </button>
                            <button disabled={isSubmitting} onClick={() => setIsEditing(true)}>
                                Edit
                            </button>
                            <button disabled={isSubmitting} onClick={() => submitDecision('rejected')}>
                                Reject
                            </button>
                        </>
                    )}
                </div>
            )}
        </main>
    )
}

export default DecisionDetail
