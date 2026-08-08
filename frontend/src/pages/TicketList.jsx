import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion, useReducedMotion } from 'framer-motion'
import { Inbox, ArrowUpRight, Plus } from 'lucide-react'
import api from '../api'
import { Button, ErrorNote, Eyebrow, Loading, Panel, Tag } from '../components/ui'
import { hairline } from '../components/tokens'

const statusTone = {
    approved: 'success',
    rejected: 'danger',
    pending_review: 'violet',
    in_review: 'violet',
    closed: 'neutral',
}

const statusLabels = { in_review: 'pending', pending_review: 'pending review' }

function TicketList() {
    const reduce = useReducedMotion()
    const [tickets, setTickets] = useState([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        api.get('/tickets/')
            .then(res => setTickets(res.data.results || res.data))
            .catch(err => setError(err.message))
            .finally(() => setIsLoading(false))
    }, [])

    if (isLoading) return <Loading label="Loading tickets" />
    if (error) return <ErrorNote>{error}</ErrorNote>

    return (
        <div>
            <div className="mb-14 flex flex-col gap-8 sm:flex-row sm:items-end sm:justify-between">
                <div>
                    <Eyebrow>{tickets.length} total</Eyebrow>
                    <h1 className="mt-6 text-[clamp(2.25rem,6vw,3.5rem)]">Your tickets</h1>
                </div>
                <Button to="/tickets/new" icon={Plus}>New ticket</Button>
            </div>

            {tickets.length === 0 ? (
                <Panel innerClassName="flex flex-col items-center gap-4 py-24 text-ink-faint">
                    <Inbox size={26} {...hairline} />
                    <p className="font-mono text-[11px] uppercase tracking-[0.2em]">Nothing here yet</p>
                </Panel>
            ) : (
                <ul className="flex flex-col gap-3">
                    {tickets.map((ticket, i) => (
                        <motion.li
                            key={ticket.id}
                            initial={reduce ? false : { opacity: 0, y: 16, filter: 'blur(4px)' }}
                            animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
                            transition={{ duration: 0.6, delay: i * 0.04, ease: [0.32, 0.72, 0, 1] }}
                        >
                            <Link to={`/tickets/${ticket.id}`} className="group block">
                                <Panel
                                    className="transition-colors duration-500 ease-fluid group-hover:bg-hairline/45"
                                    innerClassName="flex items-center justify-between gap-5 px-6 py-5"
                                >
                                    <span className="min-w-0 flex-1 truncate text-[15px] text-ink">{ticket.subject}</span>
                                    <span className="flex shrink-0 items-center gap-4">
                                        <Tag tone={statusTone[ticket.status] || 'neutral'}>
                                            {statusLabels[ticket.status] || ticket.status}
                                        </Tag>
                                        <span className="flex size-8 items-center justify-center rounded-full bg-shell text-ink-dim transition-transform duration-500 ease-fluid group-hover:translate-x-0.5 group-hover:-translate-y-px group-hover:scale-105">
                                            <ArrowUpRight size={14} {...hairline} />
                                        </span>
                                    </span>
                                </Panel>
                            </Link>
                        </motion.li>
                    ))}
                </ul>
            )}
        </div>
    )
}

export default TicketList
