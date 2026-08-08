import { Link } from 'react-router-dom'
import { motion, useReducedMotion } from 'framer-motion'
import { ArrowUpRight, Check, Pencil, X } from 'lucide-react'
import { Mark } from '../components/Layout'
import { Button, Eyebrow, Panel, Reveal, Tag } from '../components/ui'
import { hairline, urgencyTone } from '../components/tokens'

const queue = [
    { subject: 'Refund not received for order #48213', urgency: 'high', active: true },
    { subject: "Can't log in after password reset", urgency: 'medium', active: false },
    { subject: 'Webhook returning 500 intermittently', urgency: 'critical', active: false },
]

const capabilities = [
    {
        index: '01',
        title: 'Triaged before you read it',
        body: 'Category and urgency are resolved the moment a ticket lands. The queue arrives sorted, not raw.',
        span: 'md:col-span-7',
    },
    {
        index: '02',
        title: 'Answers with citations',
        body: 'The agent searches your knowledge base and drafts a reply against real sources — or escalates when it finds none.',
        span: 'md:col-span-5',
    },
    {
        index: '03',
        title: 'Nothing sends itself',
        body: 'Every proposal waits for a human. Approve it, rewrite it, or send it back — one queue, three keys.',
        span: 'md:col-span-12',
    },
]

function Landing() {
    const reduce = useReducedMotion()

    return (
        <div className="relative z-10 min-h-[100dvh]">
            <header className="sticky top-0 z-30 flex justify-center px-4 pt-5 sm:pt-6">
                <nav className="flex w-full max-w-3xl items-center justify-between gap-8 rounded-full bg-core/75 px-2 py-2 pl-5 ring-1 ring-inset ring-hairline/70 backdrop-blur-2xl sm:w-max">
                    <Mark />
                    <Link
                        to="/login"
                        className="rounded-full bg-accent px-5 py-2 text-sm font-medium text-white transition-all duration-500 ease-fluid hover:bg-accent-hover active:scale-[0.98]"
                    >
                        Sign in
                    </Link>
                </nav>
            </header>

            {/* Editorial hero — asymmetric, weighted left, breathing hard. */}
            <section className="mx-auto max-w-6xl px-4 pb-24 pt-24 sm:px-8 sm:pb-32 sm:pt-36">
                <motion.div
                    initial={reduce ? false : { opacity: 0, y: 40, filter: 'blur(10px)' }}
                    animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
                    transition={{ duration: 0.95, ease: [0.32, 0.72, 0, 1] }}
                    className="grid gap-14 md:grid-cols-12 md:items-end"
                >
                    <div className="md:col-span-8">
                        <Eyebrow>
                            <span className="size-1 rounded-full bg-accent" />
                            Human-in-the-loop support
                        </Eyebrow>
                        <h1 className="mt-7 text-[clamp(2.75rem,8vw,5.75rem)] font-medium">
                            Your queue,
                            <br />
                            <span className="text-ink-faint">mostly handled</span>
                            <br />
                            before you open it.
                        </h1>
                    </div>

                    <div className="md:col-span-4 md:pb-4">
                        <p className="text-[17px] leading-relaxed text-ink-dim">
                            Every ticket arrives prioritized, with a reply already drafted against your knowledge
                            base. Approve it, tweak it, or send it back — nothing reaches a customer without you.
                        </p>
                        <div className="mt-9">
                            <Button to="/login" icon={ArrowUpRight}>
                                Open the queue
                            </Button>
                        </div>
                    </div>
                </motion.div>
            </section>

            {/* The product itself, seated in a machined tray. */}
            <Reveal className="mx-auto max-w-6xl px-4 pb-28 sm:px-8 sm:pb-40" delay={0.05}>
                <Panel innerClassName="overflow-hidden">
                    <div className="flex items-center gap-4 border-b border-hairline/70 px-5 py-3.5">
                        <div className="flex gap-1.5">
                            <span className="size-2 rounded-full bg-hairline" />
                            <span className="size-2 rounded-full bg-hairline" />
                            <span className="size-2 rounded-full bg-hairline" />
                        </div>
                        <span className="mx-auto font-mono text-[11px] tracking-[0.08em] text-ink-faint">
                            app.triagepilot.io/triage
                        </span>
                    </div>

                    <div className="grid md:grid-cols-[300px_1fr]">
                        <div className="flex flex-col gap-1.5 border-b border-hairline/70 p-3 md:border-b-0 md:border-r">
                            {queue.map((item) => (
                                <div
                                    key={item.subject}
                                    className={`rounded-2xl p-4 transition-colors duration-500 ease-fluid
                                        ${item.active ? 'bg-shell ring-1 ring-inset ring-hairline/70' : ''}`}
                                >
                                    <p className="mb-2.5 truncate text-[13px] text-ink">{item.subject}</p>
                                    <Tag tone={urgencyTone[item.urgency]}>{item.urgency}</Tag>
                                </div>
                            ))}
                        </div>

                        <div className="p-6 sm:p-9">
                            <div className="mb-7 flex flex-wrap items-center gap-3">
                                <h3 className="text-lg">Refund not received for order #48213</h3>
                                <Tag>billing</Tag>
                            </div>

                            {[
                                {
                                    label: 'Agent reasoning',
                                    text: 'Stripe shows the refund (txn_1N2k…) completed Aug 3, but the account still reads "pending." KB-114 says refund status syncs within 24h — this is a webhook desync, not a policy issue.',
                                },
                                {
                                    label: 'Proposed reply',
                                    text: '"Hi Maria — your refund of $86.40 was processed on our end on Aug 3. Our system didn\'t sync the status back to your account; I\'ve corrected it and you should see it now. Sorry for the mix-up."',
                                },
                            ].map(({ label, text }) => (
                                <div key={label} className="mb-6">
                                    <p className="mb-2.5 font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">
                                        {label}
                                    </p>
                                    <p className="rounded-2xl bg-shell p-4 text-[13.5px] leading-relaxed text-ink-dim ring-1 ring-inset ring-hairline/70">
                                        {text}
                                    </p>
                                </div>
                            ))}

                            <div className="flex flex-wrap gap-2">
                                <span className="flex items-center gap-2 rounded-full bg-accent px-4 py-2 text-xs font-medium text-white">
                                    <Check size={13} {...hairline} /> Approve
                                </span>
                                <span className="flex items-center gap-2 rounded-full px-4 py-2 text-xs text-ink-dim ring-1 ring-inset ring-hairline/70">
                                    <Pencil size={13} {...hairline} /> Edit
                                </span>
                                <span className="flex items-center gap-2 rounded-full px-4 py-2 text-xs text-ink-dim ring-1 ring-inset ring-hairline/70">
                                    <X size={13} {...hairline} /> Reject
                                </span>
                            </div>
                        </div>
                    </div>
                </Panel>
                <p className="mt-5 text-center font-mono text-[11px] uppercase tracking-[0.18em] text-ink-faint">
                    The real queue, on a real ticket
                </p>
            </Reveal>

            {/* Asymmetrical bento. */}
            <section className="mx-auto max-w-6xl px-4 pb-28 sm:px-8 sm:pb-40">
                <Reveal className="mb-16 max-w-xl">
                    <Eyebrow>What it does</Eyebrow>
                    <h2 className="mt-6 text-[clamp(2rem,5vw,3.25rem)]">
                        Three steps, and only one of them is yours.
                    </h2>
                </Reveal>

                <div className="grid gap-4 md:grid-cols-12">
                    {capabilities.map(({ index, title, body, span }, i) => (
                        <Reveal key={index} delay={i * 0.08} className={`col-span-1 ${span}`}>
                            <Panel className="h-full" innerClassName="flex h-full flex-col p-8 sm:p-10">
                                <span className="font-mono text-[11px] tracking-[0.2em] text-accent">{index}</span>
                                <h3 className="mt-6 max-w-sm text-2xl">{title}</h3>
                                <p className="mt-4 max-w-md text-[15px] leading-relaxed text-ink-dim">{body}</p>
                            </Panel>
                        </Reveal>
                    ))}
                </div>
            </section>

            <section className="mx-auto max-w-6xl px-4 pb-28 sm:px-8 sm:pb-40">
                <Reveal>
                    <Panel innerClassName="flex flex-col items-start gap-9 p-10 sm:p-16">
                        <h2 className="max-w-2xl text-[clamp(1.9rem,4.5vw,3rem)]">
                            Stop reading tickets cold.
                        </h2>
                        <Button to="/login" icon={ArrowUpRight}>
                            Sign in
                        </Button>
                    </Panel>
                </Reveal>
            </section>

            <footer className="mx-auto flex max-w-6xl flex-col gap-4 border-t border-hairline/70 px-4 py-10 text-ink-faint sm:flex-row sm:items-center sm:justify-between sm:px-8">
                <Mark className="text-ink-dim" />
                <p className="font-mono text-[11px] uppercase tracking-[0.18em]">Human-approved by default</p>
            </footer>
        </div>
    )
}

export default Landing
