import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { Check, Pencil, X, ArrowLeft, FileText } from 'lucide-react'
import api from '../api'
import { Button, ErrorNote, Eyebrow, Loading, Panel, Tag } from '../components/ui'
import { fieldClass, hairline, urgencyTone } from '../components/tokens'
import MessageThread from '../components/MessageThread'

function Block({ label, children, className = '' }) {
    return (
        <div className={className}>
            <p className="mb-3 font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">{label}</p>
            {children}
        </div>
    )
}

function Quote({ children }) {
    return (
        <p className="whitespace-pre-wrap rounded-2xl bg-shell p-5 text-[14.5px] leading-relaxed text-ink-dim ring-1 ring-inset ring-hairline/70">
            {children}
        </p>
    )
}

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

    if (isLoading) return <Loading />
    if (error && !decision) return <ErrorNote>{error}</ErrorNote>
    if (!decision) return null

    const { ticket } = decision
    const alreadyDecided = Boolean(decision.human_decision)

    const sources = Array.isArray(decision.sources_used)
        ? decision.sources_used
        : decision.sources_used ? [decision.sources_used] : []

    return (
        <div className="pb-28">
            <Link
                to="/triage"
                className="group inline-flex items-center gap-2.5 text-sm text-ink-faint transition-colors duration-500 ease-fluid hover:text-ink"
            >
                <span className="flex size-8 items-center justify-center rounded-full bg-shell transition-transform duration-500 ease-fluid group-hover:-translate-x-0.5">
                    <ArrowLeft size={14} {...hairline} />
                </span>
                Back to queue
            </Link>

            <div className="mt-12 mb-12 max-w-3xl">
                <div className="flex flex-wrap items-center gap-2.5">
                    <Eyebrow>{alreadyDecided ? `Decided · ${decision.human_decision}` : 'Awaiting review'}</Eyebrow>
                    <Tag tone={urgencyTone[ticket.urgency] || 'neutral'}>{ticket.urgency || 'unset'}</Tag>
                    <Tag>{ticket.category || 'uncategorized'}</Tag>
                </div>
                <h1 className="mt-7 text-[clamp(1.9rem,5vw,3.25rem)]">{ticket.subject}</h1>
                <p className="mt-3 text-sm text-ink-faint">
                    Submitted by {ticket.created_by_username || 'an unknown user'}
                </p>
            </div>

            {error && <div className="mb-8"><ErrorNote>{error}</ErrorNote></div>}

            <div className="grid gap-4 md:grid-cols-12">
                <Panel className="md:col-span-5" innerClassName="flex h-full flex-col gap-8 p-8 sm:p-9">
                    <Block label="What the customer wrote">
                        <Quote>{ticket.body}</Quote>
                    </Block>

                    <Block label="Sources cited" className="mt-auto">
                        {sources.length > 0 ? (
                            <ul className="flex flex-col gap-2">
                                {sources.map((source, i) => (
                                    <li
                                        key={i}
                                        className="flex items-start gap-3 rounded-2xl bg-shell px-4 py-3 text-[13px] text-ink-dim ring-1 ring-inset ring-hairline/70"
                                    >
                                        <FileText size={14} {...hairline} className="mt-0.5 shrink-0 text-accent" />
                                        {typeof source === 'string' ? source : JSON.stringify(source)}
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <p className="text-sm text-ink-faint">No sources cited — the agent escalated instead.</p>
                        )}
                    </Block>
                </Panel>

                <Panel className="md:col-span-7" innerClassName="flex h-full flex-col gap-8 p-8 sm:p-9">
                    <Block label="Agent reasoning">
                        <Quote>{decision.agent_reasoning}</Quote>
                    </Block>

                    <Block label={isEditing ? 'Proposed action — editing' : 'Proposed action'}>
                        {isEditing ? (
                            <textarea
                                value={editedText}
                                onChange={e => setEditedText(e.target.value)}
                                rows={10}
                                className={`${fieldClass} resize-y p-5 leading-relaxed`}
                            />
                        ) : (
                            <Quote>{decision.edited_action || decision.proposed_action}</Quote>
                        )}
                    </Block>
                </Panel>
            </div>

            {alreadyDecided && decision.human_decision !== 'rejected' && (
                <MessageThread ticketId={ticket.id} />
            )}

            {!alreadyDecided && (
                /* Decision island — floats over the content, never welded to the edge. */
                <div className="pointer-events-none fixed inset-x-0 bottom-0 z-20 flex justify-center px-4 pb-6">
                    <div className="pointer-events-auto flex flex-wrap items-center justify-center gap-2 rounded-full bg-core/75 p-2 ring-1 ring-inset ring-hairline/70 backdrop-blur-2xl">
                        {isEditing ? (
                            <>
                                <Button
                                    icon={Check}
                                    disabled={isSubmitting}
                                    loading={isSubmitting}
                                    onClick={() => submitDecision('edited')}
                                >
                                    Save &amp; approve
                                </Button>
                                <Button
                                    variant="ghost"
                                    icon={X}
                                    disabled={isSubmitting}
                                    onClick={() => { setIsEditing(false); setEditedText(decision.proposed_action) }}
                                >
                                    Cancel
                                </Button>
                            </>
                        ) : (
                            <>
                                <Button
                                    icon={Check}
                                    disabled={isSubmitting}
                                    loading={isSubmitting}
                                    onClick={() => submitDecision('approved')}
                                >
                                    Approve
                                </Button>
                                <Button variant="ghost" icon={Pencil} disabled={isSubmitting} onClick={() => setIsEditing(true)}>
                                    Edit
                                </Button>
                                <Button variant="danger" icon={X} disabled={isSubmitting} onClick={() => submitDecision('rejected')}>
                                    Reject
                                </Button>
                            </>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}

export default DecisionDetail
