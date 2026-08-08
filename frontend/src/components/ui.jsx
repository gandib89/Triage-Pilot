import { motion, useReducedMotion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { LoaderCircle } from 'lucide-react'
import { hairline } from './tokens'

const FLUID = [0.32, 0.72, 0, 1]

/**
 * Double-bezel enclosure: an outer tray with a hairline lip, holding an inner
 * core with its own catch-light. Concentric radii — core = shell - padding.
 */
export function Panel({ children, className = '', innerClassName = '', as: Tag = 'div', ...rest }) {
    return (
        <Tag className={`rounded-shell bg-shell p-1.5 ring-1 ring-hairline/70 ${className}`} {...rest}>
            <div className={`bevel rounded-core bg-core ${innerClassName}`}>
                {children}
            </div>
        </Tag>
    )
}

const variants = {
    accent: 'bg-accent text-white hover:bg-accent-hover',
    ghost: 'bg-shell text-ink ring-1 ring-inset ring-hairline/70 hover:bg-hairline/50',
    danger: 'bg-danger/12 text-danger ring-1 ring-inset ring-danger/25 hover:bg-danger/18',
}

const nestedTone = {
    accent: 'bg-white/25',
    ghost: 'bg-hairline/55',
    danger: 'bg-danger/15',
}

/**
 * Island button. A trailing icon never sits naked — it lives inside its own
 * circular well, flush with the pill's inner padding, and drifts on hover.
 */
export function Button({
    children,
    icon: Icon,
    variant = 'accent',
    to,
    loading = false,
    className = '',
    ...rest
}) {
    const Root = to ? Link : 'button'

    return (
        <Root
            {...(to ? { to } : { type: 'button' })}
            {...rest}
            className={`group inline-flex cursor-pointer items-center gap-3 rounded-full py-2 pl-6 text-sm font-medium
                transition-all duration-500 ease-fluid active:scale-[0.98]
                disabled:cursor-not-allowed disabled:opacity-45 disabled:active:scale-100
                ${Icon || loading ? 'pr-2' : 'pr-6'} ${variants[variant]} ${className}`}
        >
            {children}
            {(Icon || loading) && (
                <span
                    className={`flex size-8 items-center justify-center rounded-full transition-transform duration-500 ease-fluid
                        group-hover:translate-x-0.5 group-hover:-translate-y-px group-hover:scale-105 ${nestedTone[variant]}`}
                >
                    {loading
                        ? <LoaderCircle size={15} {...hairline} className="animate-spin" />
                        : <Icon size={15} {...hairline} />}
                </span>
            )}
        </Root>
    )
}

/** Microscopic pill that precedes a heading. */
export function Eyebrow({ children, className = '' }) {
    return (
        <span
            className={`inline-flex items-center gap-2 rounded-full bg-shell px-3 py-1 text-[10px]
                font-medium uppercase tracking-[0.2em] text-ink-dim ring-1 ring-inset ring-hairline/70 ${className}`}
        >
            {children}
        </span>
    )
}

const tones = {
    neutral: 'bg-shell text-ink-dim ring-hairline/70',
    accent: 'bg-accent/10 text-accent ring-accent/20',
    success: 'bg-success/12 text-success ring-success/25',
    danger: 'bg-danger/10 text-danger ring-danger/25',
    amber: 'bg-amber/10 text-amber ring-amber/25',
    violet: 'bg-violet/10 text-violet ring-violet/25',
}

export function Tag({ children, tone = 'neutral', className = '' }) {
    return (
        <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 font-mono text-[10px] uppercase
                tracking-[0.12em] ring-1 ring-inset ${tones[tone]} ${className}`}
        >
            {children}
        </span>
    )
}

export function Field({ label, hint, className = '', children }) {
    return (
        <label className={`flex flex-col gap-2 ${className}`}>
            <span className="flex items-baseline justify-between text-[11px] font-medium uppercase tracking-[0.16em] text-ink-faint">
                {label}
                {hint && <span className="tracking-normal normal-case">{hint}</span>}
            </span>
            {children}
        </label>
    )
}

/** Heavy fade-up on viewport entry. Transform + opacity + filter only. */
export function Reveal({ children, delay = 0, className = '', ...rest }) {
    const reduce = useReducedMotion()

    return (
        <motion.div
            initial={reduce ? false : { opacity: 0, y: 48, filter: 'blur(8px)' }}
            whileInView={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
            viewport={{ once: true, amount: 0.15 }}
            transition={{ duration: 0.85, delay, ease: FLUID }}
            className={className}
            {...rest}
        >
            {children}
        </motion.div>
    )
}

export function Loading({ label = 'Loading' }) {
    return (
        <div className="flex items-center gap-3 py-24 text-sm text-ink-dim">
            <LoaderCircle size={16} {...hairline} className="animate-spin text-accent" />
            <span className="font-mono text-[11px] uppercase tracking-[0.2em]">{label}</span>
        </div>
    )
}

export function ErrorNote({ children }) {
    return (
        <p className="rounded-2xl bg-danger/[0.07] px-4 py-3 text-sm text-danger ring-1 ring-inset ring-danger/20">
            {children}
        </p>
    )
}
