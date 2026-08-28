import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Inbox, ListChecks, LogOut } from 'lucide-react'
import api from '../api'
import { isStaff, setAccessToken } from '../auth'
import PageFade from './PageFade'
import { hairline } from './tokens'

export function Mark({ className = '' }) {
    return (
        <span className={`flex items-center gap-2.5 ${className}`}>
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
                <path
                    d="M9 1.4 15.6 4.3v5.1c0 3.4-2.6 6.3-6.6 7.2-4-0.9-6.6-3.8-6.6-7.2V4.3L9 1.4Z"
                    stroke="currentColor"
                    strokeWidth="1.1"
                    className="text-accent"
                />
                <path d="M6.2 9.1 8.3 11.2 12 6.9" stroke="currentColor" strokeWidth="1.1" className="text-accent" />
            </svg>
            <span className="text-[15px] font-medium tracking-[-0.02em]">TriagePilot</span>
        </span>
    )
}

function NavPill({ to, active, icon: Icon, children, onClick }) {
    return (
        <Link
            to={to}
            onClick={onClick}
            className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm transition-all duration-500 ease-fluid
                ${active ? 'bg-shell text-ink' : 'text-ink-dim hover:text-ink'}`}
        >
            <Icon size={15} {...hairline} className={active ? 'text-accent' : ''} />
            {children}
        </Link>
    )
}

function Layout({ children }) {
    const navigate = useNavigate()
    const location = useLocation()
    const [open, setOpen] = useState(false)
    const staff = isStaff()
    const homePath = staff ? '/triage' : '/tickets'

    const handleLogout = async () => {
        try {
            await api.post('/logout/')
        } catch {
            // Session's dead either way — still clear client state and leave.
        }
        setAccessToken(null)
        navigate('/login')
    }

    const primary = staff
        ? { to: '/triage', icon: ListChecks, label: 'Triage queue' }
        : { to: '/tickets', icon: Inbox, label: 'Tickets' }
    const active = location.pathname.startsWith(primary.to)

    return (
        <div className="relative min-h-[100dvh]">
            {/* Fluid island — detached from the top edge, glass, never glued. */}
            <header className="sticky top-0 z-30 flex justify-center px-4 pt-5 sm:pt-6">
                <nav
                    className="flex w-full max-w-3xl items-center justify-between gap-6 rounded-full
                        bg-core/75 px-2 py-2 pl-5 ring-1 ring-inset ring-hairline/70 backdrop-blur-2xl sm:w-max"
                >
                    <Link to={homePath} className="text-ink transition-opacity duration-500 ease-fluid hover:opacity-70">
                        <Mark />
                    </Link>

                    <div className="hidden items-center gap-1 sm:flex">
                        <NavPill to={primary.to} active={active} icon={primary.icon}>
                            {primary.label}
                        </NavPill>
                        <button
                            onClick={handleLogout}
                            className="flex cursor-pointer items-center gap-2 rounded-full px-4 py-2 text-sm text-ink-dim
                                transition-colors duration-500 ease-fluid hover:text-ink"
                        >
                            <LogOut size={15} {...hairline} />
                            Sign out
                        </button>
                    </div>

                    {/* Hamburger that morphs into an X rather than swapping glyphs. */}
                    <button
                        onClick={() => setOpen(!open)}
                        aria-label={open ? 'Close menu' : 'Open menu'}
                        aria-expanded={open}
                        className="relative flex size-9 cursor-pointer items-center justify-center rounded-full
                            bg-shell transition-colors duration-500 ease-fluid hover:bg-hairline/50 sm:hidden"
                    >
                        <span
                            className={`absolute h-px w-4 bg-ink transition-transform duration-500 ease-fluid
                                ${open ? 'rotate-45' : '-translate-y-[3px]'}`}
                        />
                        <span
                            className={`absolute h-px w-4 bg-ink transition-transform duration-500 ease-fluid
                                ${open ? '-rotate-45' : 'translate-y-[3px]'}`}
                        />
                    </button>
                </nav>
            </header>

            {/* Screen-filling glass overlay with staggered mask reveal. */}
            <div
                className={`fixed inset-0 z-20 bg-core/85 backdrop-blur-3xl transition-opacity duration-700 ease-fluid sm:hidden
                    ${open ? 'opacity-100' : 'pointer-events-none opacity-0'}`}
            >
                <div className="flex min-h-[100dvh] flex-col justify-center gap-2 px-8">
                    {[
                        <NavPill key="primary" to={primary.to} active={active} icon={primary.icon} onClick={() => setOpen(false)}>
                            <span className="text-3xl tracking-[-0.03em]">{primary.label}</span>
                        </NavPill>,
                        <button
                            key="logout"
                            onClick={handleLogout}
                            className="flex cursor-pointer items-center gap-2 px-4 py-2 text-3xl tracking-[-0.03em] text-ink-dim"
                        >
                            <LogOut size={18} {...hairline} />
                            Sign out
                        </button>,
                    ].map((item, i) => (
                        <div
                            key={item.key}
                            style={{ transitionDelay: `${open ? 120 + i * 70 : 0}ms` }}
                            className={`transition-all duration-700 ease-fluid
                                ${open ? 'translate-y-0 opacity-100' : 'translate-y-12 opacity-0'}`}
                        >
                            {item}
                        </div>
                    ))}
                </div>
            </div>

            <main className="relative z-10 mx-auto w-full max-w-6xl px-4 pb-32 pt-14 sm:px-8 sm:pt-24">
                <PageFade key={location.pathname}>{children}</PageFade>
            </main>
        </div>
    )
}

export default Layout
