// Non-component design constants. Kept out of ui.jsx so that file stays
// component-only and Fast Refresh keeps working.

// Every icon in the app is hairline-weight. Spread onto lucide icons rather
// than pulling in a second icon set.
export const hairline = { strokeWidth: 1.25 }

export const fieldClass =
    `field w-full rounded-2xl border border-hairline bg-core px-4 py-3 text-sm text-ink
     outline-none transition-[border-color,box-shadow] duration-400 ease-fluid
     placeholder:text-ink-faint`

export const urgencyTone = { critical: 'danger', high: 'danger', medium: 'amber', low: 'neutral' }

// A DecisionLog row is created the moment a ticket is submitted, then filled
// in by the agent in the background — so a row in the queue is in one of
// three states, and only 'ready' can be acted on.
export const triageState = d =>
    d.triage_error ? 'failed' : d.proposed_action ? 'ready' : 'running'

export const triageTone = { failed: 'danger', running: 'amber', ready: 'neutral' }
