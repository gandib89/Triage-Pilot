import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import dayjs from 'dayjs'
import { Archive, ArrowLeft, FileText } from 'lucide-react'
import api from '../api'
import { Button, ErrorNote, Eyebrow, Loading, Panel, Tag } from '../components/ui'
import { hairline } from '../components/tokens'
import MessageThread from '../components/MessageThread'

const statusTone = { approved: 'success', rejected: 'danger', pending: 'violet', closed: 'neutral' }
const KNOWN_STATUSES = ['approved', 'rejected', 'closed']

function displayStatus(status) {
    return KNOWN_STATUSES.includes(status) ? status : 'pending'
}

function TicketDetail() {
    const { id } = useParams()
    const [ticket, setTicket] = useState(null)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState(null)
    const [isClosing, setIsClosing] = useState(false)

    useEffect(() => {
        api.get(`/tickets/${id}/`)
            .then(res => setTicket(res.data))
            .catch(err => setError(err.message))
            .finally(() => setIsLoading(false))
    }, [id])

    const closeTicket = async () => {
        setIsClosing(true)
        setError(null)
        try {
            const res = await api.post(`/tickets/${id}/close/`)
            setTicket(res.data)
        } catch (err) {
            setError(err.response?.data?.detail || err.message)
        } finally {
            setIsClosing(false)
        }
    }

    if (isLoading) return <Loading />
    if (error && !ticket) return <ErrorNote>{error}</ErrorNote>

    const status = displayStatus(ticket.status)
    const { resolution } = ticket
    const sources = Array.isArray(resolution?.sources)
        ? resolution.sources
        : resolution?.sources ? [resolution.sources] : []

    return (
        <div>
            <Link
                to="/tickets"
                className="group inline-flex items-center gap-2.5 text-sm text-ink-faint transition-colors duration-500 ease-fluid hover:text-ink"
            >
                <span className="flex size-8 items-center justify-center rounded-full bg-shell transition-transform duration-500 ease-fluid group-hover:-translate-x-0.5">
                    <ArrowLeft size={14} {...hairline} />
                </span>
                Back to tickets
            </Link>

            <div className="mt-12 mb-14 max-w-3xl">
                <Eyebrow>
                    <span className={`size-1 rounded-full ${status === 'approved' ? 'bg-success' : status === 'rejected' ? 'bg-danger' : status === 'closed' ? 'bg-ink-faint' : 'bg-violet'}`} />
                    {status}
                </Eyebrow>
                <h1 className="mt-6 text-[clamp(2rem,5vw,3.25rem)]">{ticket.subject}</h1>
            </div>

            {error && <div className="mb-8"><ErrorNote>{error}</ErrorNote></div>}

            <div className="grid gap-4 md:grid-cols-12">
                <Panel className="md:col-span-8" innerClassName="p-8 sm:p-10">
                    <p className="mb-5 font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">Description</p>
                    <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-ink-dim">{ticket.body}</p>
                </Panel>

                <Panel className="md:col-span-4" innerClassName="flex h-full flex-col gap-7 p-8 sm:p-10">
                    <div>
                        <p className="mb-3 font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">Status</p>
                        <Tag tone={statusTone[status]}>{status}</Tag>
                    </div>
                    <div>
                        <p className="mb-3 font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">Submitted</p>
                        <p className="text-sm text-ink-dim">{dayjs(ticket.created_at).format('MMM D, YYYY · h:mm A')}</p>
                    </div>
                    {status !== 'closed' && (
                        <Button
                            variant="ghost"
                            icon={Archive}
                            className="mt-auto"
                            disabled={isClosing}
                            loading={isClosing}
                            onClick={closeTicket}
                        >
                            Close ticket
                        </Button>
                    )}
                </Panel>
            </div>

            {resolution && (
                <Panel className="mt-4" innerClassName="flex flex-col gap-6 p-8 sm:p-10">
                    <div>
                        <p className="mb-3 font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">Response from support</p>
                        <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-ink-dim">{resolution.reply}</p>
                    </div>
                    {sources.length > 0 && (
                        <ul className="flex flex-wrap gap-2">
                            {sources.map((source, i) => (
                                <li
                                    key={i}
                                    className="flex items-center gap-2 rounded-full bg-shell px-3 py-1.5 text-[12px] text-ink-dim ring-1 ring-inset ring-hairline/70"
                                >
                                    <FileText size={12} {...hairline} className="text-accent" />
                                    {typeof source === 'string' ? source : JSON.stringify(source)}
                                </li>
                            ))}
                        </ul>
                    )}
                </Panel>
            )}

            {resolution && <MessageThread ticketId={ticket.id} />}
        </div>
    )
}

export default TicketDetail
