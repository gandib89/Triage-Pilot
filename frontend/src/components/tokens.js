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
