import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion, useReducedMotion } from 'framer-motion'
import { ListChecks, ArrowUpRight } from 'lucide-react'
import api from '../api'
import { ErrorNote, Eyebrow, Loading, Panel, Tag } from '../components/ui'
import { hairline, urgencyTone } from '../components/tokens'

function TriageQueue() {
    const reduce = useReducedMotion()
    const [decisions, setDecisions] = useState([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        api.get('/decisions/?status=pending')
            .then(res => setDecisions(res.data.results || res.data))
            .catch(err => setError(err.message))
            .finally(() => setIsLoading(false))
    }, [])

    if (isLoading) return <Loading label="Loading queue" />
    if (error) return <ErrorNote>{error}</ErrorNote>

    return (
        <div>
            <div className="mb-14">
                <Eyebrow>
                    <span className="size-1 rounded-full bg-accent" />
                    {decisions.length} awaiting review
                </Eyebrow>
                <h1 className="mt-6 text-[clamp(2.25rem,6vw,3.5rem)]">Triage queue</h1>
            </div>

            {decisions.length === 0 ? (
                <Panel innerClassName="flex flex-col items-center gap-4 py-24 text-ink-faint">
                    <ListChecks size={26} {...hairline} />
                    <p className="font-mono text-[11px] uppercase tracking-[0.2em]">Queue clear</p>
                </Panel>
            ) : (
                <ul className="flex flex-col gap-3">
                    {decisions.map((decision, i) => (
                        <motion.li
                            key={decision.id}
                            initial={reduce ? false : { opacity: 0, y: 16, filter: 'blur(4px)' }}
                            animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
                            transition={{ duration: 0.6, delay: i * 0.04, ease: [0.32, 0.72, 0, 1] }}
                        >
                            <Link to={`/triage/${decision.id}`} className="group block">
                                <Panel
                                    className="transition-colors duration-500 ease-fluid group-hover:bg-hairline/45"
                                    innerClassName="flex items-start justify-between gap-6 px-6 py-6"
                                >
                                    <div className="min-w-0">
                                        <div className="mb-3 flex flex-wrap items-center gap-2.5">
                                            <span className="text-[15px] text-ink">{decision.ticket.subject}</span>
                                            <Tag tone={urgencyTone[decision.ticket.urgency] || 'neutral'}>
                                                {decision.ticket.urgency || 'unset'}
                                            </Tag>
                                            <Tag>{decision.ticket.category || 'uncategorized'}</Tag>
                                        </div>
                                        <p className="truncate text-sm text-ink-faint">{decision.proposed_action}</p>
                                    </div>
                                    <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-shell text-ink-dim transition-transform duration-500 ease-fluid group-hover:translate-x-0.5 group-hover:-translate-y-px group-hover:scale-105">
                                        <ArrowUpRight size={14} {...hairline} />
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

export default TriageQueue
