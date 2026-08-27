import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowUpRight } from 'lucide-react'
import api from '../api'
import { Button, ErrorNote, Eyebrow, Field, Panel } from '../components/ui'
import { fieldClass, hairline } from '../components/tokens'

function NewTicket() {
    const [subject, setSubject] = useState('')
    const [body, setBody] = useState('')
    const [error, setError] = useState(null)
    const [isSubmitting, setIsSubmitting] = useState(false)
    const navigate = useNavigate()

    // Triage is kicked off server-side on create and runs in the background,
    // so submitting is one request and the customer never waits on the agent.
    const handleSubmit = async (e) => {
        e.preventDefault()
        setError(null)
        setIsSubmitting(true)
        try {
            const res = await api.post('/tickets/', { subject, body })
            navigate(`/tickets/${res.data.id}`)
        } catch (err) {
            setError(err.response?.data ? JSON.stringify(err.response.data) : err.message)
            setIsSubmitting(false)
        }
    }

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

            <div className="mx-auto mt-12 max-w-2xl">
                <Eyebrow>New ticket</Eyebrow>
                <h1 className="mt-6 text-[clamp(2rem,5vw,3.25rem)]">Tell us what broke.</h1>
                <p className="mt-5 max-w-lg text-[15px] leading-relaxed text-ink-dim">
                    The agent categorizes it, searches the knowledge base, and drafts a next step — which a
                    human reviews before anything is sent back to you.
                </p>

                <Panel className="mt-12" innerClassName="p-8 sm:p-10">
                    <form onSubmit={handleSubmit} className="flex flex-col gap-6">
                        <Field label="Subject">
                            <input
                                type="text"
                                value={subject}
                                onChange={(e) => setSubject(e.target.value)}
                                required
                                placeholder="Short summary of the issue"
                                className={fieldClass}
                            />
                        </Field>
                        <Field label="Details">
                            <textarea
                                value={body}
                                onChange={(e) => setBody(e.target.value)}
                                required
                                rows={9}
                                placeholder="Steps to reproduce, error messages, order or account references — anything that pins down the issue."
                                className={`${fieldClass} resize-y leading-relaxed`}
                            />
                        </Field>

                        {error && <ErrorNote>{error}</ErrorNote>}

                        <Button
                            type="submit"
                            icon={ArrowUpRight}
                            loading={isSubmitting}
                            disabled={isSubmitting}
                            className="mt-1 self-start"
                        >
                            {isSubmitting ? 'Submitting' : 'Submit ticket'}
                        </Button>
                    </form>
                </Panel>
            </div>
        </div>
    )
}

export default NewTicket
