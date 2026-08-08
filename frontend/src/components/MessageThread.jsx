import { useState, useEffect, useRef } from 'react'
import { Check, Send } from 'lucide-react'
import dayjs from 'dayjs'
import api from '../api'
import { Button, ErrorNote, Panel } from './ui'
import { fieldClass } from './tokens'

/** Follow-up thread on a ticket, shared by the customer and staff views. */
function MessageThread({ ticketId }) {
    const [messages, setMessages] = useState([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState(null)
    const [draft, setDraft] = useState('')
    const [isSending, setIsSending] = useState(false)
    const [justSent, setJustSent] = useState(false)
    const sentTimeout = useRef(null)

    useEffect(() => {
        api.get(`/tickets/${ticketId}/messages/`)
            .then(res => setMessages(res.data))
            .catch(err => setError(err.message))
            .finally(() => setIsLoading(false))
    }, [ticketId])

    useEffect(() => () => clearTimeout(sentTimeout.current), [])

    const send = async () => {
        if (!draft.trim()) return
        setIsSending(true)
        setError(null)
        try {
            const res = await api.post(`/tickets/${ticketId}/messages/`, { body: draft })
            setMessages(prev => [...prev, res.data])
            setDraft('')
            setJustSent(true)
            sentTimeout.current = setTimeout(() => setJustSent(false), 1500)
        } catch (err) {
            setError(err.response?.data ? JSON.stringify(err.response.data) : err.message)
        } finally {
            setIsSending(false)
        }
    }

    return (
        <Panel className="mt-4" innerClassName="flex flex-col gap-6 p-8 sm:p-10">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">Follow-up</p>

            {isLoading ? (
                <p className="text-sm text-ink-faint">Loading messages…</p>
            ) : messages.length === 0 ? (
                <p className="text-sm text-ink-faint">No follow-up messages yet.</p>
            ) : (
                <ul className="flex flex-col gap-4">
                    {messages.map(message => (
                        <li key={message.id} className="rounded-2xl bg-shell p-4 ring-1 ring-inset ring-hairline/70">
                            <div className="mb-1.5 flex items-center justify-between gap-3">
                                <span className="text-[13px] font-medium text-ink">
                                    {message.sender_username}
                                    {message.sender_role !== 'customer' && (
                                        <span className="ml-2 font-mono text-[10px] uppercase tracking-[0.14em] text-accent">staff</span>
                                    )}
                                </span>
                                <span className="text-[12px] text-ink-faint">{dayjs(message.created_at).format('MMM D · h:mm A')}</span>
                            </div>
                            <p className="whitespace-pre-wrap text-[14px] leading-relaxed text-ink-dim">{message.body}</p>
                        </li>
                    ))}
                </ul>
            )}

            {error && <ErrorNote>{error}</ErrorNote>}

            <div className="flex items-end gap-3">
                <textarea
                    value={draft}
                    onChange={e => setDraft(e.target.value)}
                    placeholder="Write a follow-up…"
                    rows={2}
                    className={`${fieldClass} resize-none`}
                />
                <Button
                    icon={justSent ? Check : Send}
                    disabled={isSending || !draft.trim()}
                    loading={isSending}
                    onClick={send}
                >
                    {justSent ? 'Sent' : 'Send'}
                </Button>
            </div>
        </Panel>
    )
}

export default MessageThread
