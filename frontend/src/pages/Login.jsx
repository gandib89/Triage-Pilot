import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { jwtDecode } from 'jwt-decode'
import { ArrowUpRight } from 'lucide-react'
import api from '../api'
import { STAFF_ROLES, setAccessToken } from '../auth'
import PageFade from '../components/PageFade'
import { Mark } from '../components/Layout'
import { Button, ErrorNote, Eyebrow, Field, Panel } from '../components/ui'
import { fieldClass } from '../components/tokens'

function Login() {
    const [mode, setMode] = useState('signin') // 'signin' | 'signup' | 'verify'
    const [username, setUsername] = useState('')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [otp, setOtp] = useState('')
    const [error, setError] = useState(null)
    const [info, setInfo] = useState(null)
    const [isLoading, setIsLoading] = useState(false)
    const [resendCooldown, setResendCooldown] = useState(0)
    const navigate = useNavigate()

    useEffect(() => {
        if (resendCooldown <= 0) return
        const t = setInterval(() => setResendCooldown((s) => Math.max(0, s - 1)), 1000)
        return () => clearInterval(t)
    }, [resendCooldown])

    const extractError = (err, fallback) => {
        const data = err.response?.data
        if (data && typeof data === 'object') {
            return Object.values(data).flat().join(' ')
        }
        return fallback
    }

    const signIn = async () => {
        try {
            const res = await api.post('/token/', { username, password })
            const role = jwtDecode(res.data.access).role || 'customer'
            setAccessToken(res.data.access)
            navigate(STAFF_ROLES.includes(role) ? '/triage' : '/tickets')
        } catch (err) {
            const code = err.response?.data?.code?.[0]
            if (code === 'email_not_verified') {
                setMode('verify')
                setInfo('Enter the code we emailed you to finish signing in.')
                return
            }
            throw err
        }
    }

    const signUp = async () => {
        await api.post('/register/', { username, email, password })
        setMode('verify')
        setInfo(`We sent a 6-digit code to ${email}.`)
        setResendCooldown(60)
    }

    const verify = async () => {
        await api.post('/verify-otp/', { username, otp })
        await signIn()
    }

    const resendCode = async () => {
        setError(null)
        setInfo(null)
        try {
            await api.post('/resend-otp/', { username })
            setInfo('A new code is on its way.')
            setResendCooldown(60)
        } catch (err) {
            setError(extractError(err, 'Could not resend the code.'))
        }
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        setIsLoading(true)
        setError(null)
        setInfo(null)

        try {
            if (mode === 'signup') {
                await signUp()
            } else if (mode === 'verify') {
                await verify()
            } else {
                await signIn()
            }
        } catch (err) {
            setError(extractError(
                err,
                mode === 'signup' ? 'Could not create account.'
                    : mode === 'verify' ? 'Could not verify that code.'
                        : 'Invalid username or password'
            ))
        } finally {
            setIsLoading(false)
        }
    }

    const switchMode = (next) => {
        setMode(next)
        setError(null)
        setInfo(null)
    }

    const heading = mode === 'verify' ? 'Check your email'
        : mode === 'signup' ? 'Create your account'
            : 'Welcome back'

    return (
        <div className="relative z-10 flex min-h-[100dvh] flex-col px-4 py-8 sm:px-8">
            <Link to="/" className="text-ink transition-opacity duration-500 ease-fluid hover:opacity-70">
                <Mark />
            </Link>

            <div className="flex flex-1 items-center justify-center py-16">
                <PageFade>
                    <div className="w-full max-w-[26rem]">
                        <Panel innerClassName="p-8 sm:p-10">
                            <Eyebrow>{mode === 'verify' ? 'Verify' : mode === 'signup' ? 'Sign up' : 'Sign in'}</Eyebrow>
                            <h1 className="mt-6 text-[2rem]">{heading}</h1>
                            <p className="mt-3 text-sm leading-relaxed text-ink-dim">
                                {mode === 'verify'
                                    ? info || `Enter the code we sent to confirm ${username}.`
                                    : mode === 'signup'
                                        ? 'One account for submitting tickets and tracking their outcome.'
                                        : 'Pick up the queue where you left it.'}
                            </p>

                            <form onSubmit={handleSubmit} className="mt-9 flex flex-col gap-5">
                                {mode === 'verify' ? (
                                    <Field label="6-digit code">
                                        <input
                                            type="text"
                                            inputMode="numeric"
                                            autoComplete="one-time-code"
                                            maxLength={6}
                                            value={otp}
                                            onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                                            required
                                            className={`${fieldClass} text-center font-mono text-xl tracking-[0.55em]`}
                                        />
                                    </Field>
                                ) : (
                                    <>
                                        <Field label="Username">
                                            <input
                                                type="text"
                                                value={username}
                                                onChange={(e) => setUsername(e.target.value)}
                                                required
                                                autoComplete="username"
                                                className={fieldClass}
                                            />
                                        </Field>
                                        {mode === 'signup' && (
                                            <Field label="Email">
                                                <input
                                                    type="email"
                                                    value={email}
                                                    onChange={(e) => setEmail(e.target.value)}
                                                    required
                                                    autoComplete="email"
                                                    className={fieldClass}
                                                />
                                            </Field>
                                        )}
                                        <Field label="Password" hint={mode === 'signup' ? '8+ characters' : undefined}>
                                            <input
                                                type="password"
                                                value={password}
                                                onChange={(e) => setPassword(e.target.value)}
                                                required
                                                minLength={mode === 'signup' ? 8 : undefined}
                                                autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                                                className={fieldClass}
                                            />
                                        </Field>
                                    </>
                                )}

                                {error && <ErrorNote>{error}</ErrorNote>}

                                <Button
                                    type="submit"
                                    icon={ArrowUpRight}
                                    loading={isLoading}
                                    disabled={isLoading || (mode === 'verify' && otp.length !== 6)}
                                    className="mt-1 self-start"
                                >
                                    {mode === 'verify'
                                        ? isLoading ? 'Verifying' : 'Verify & sign in'
                                        : mode === 'signup'
                                            ? isLoading ? 'Creating account' : 'Create account'
                                            : isLoading ? 'Signing in' : 'Sign in'}
                                </Button>
                            </form>
                        </Panel>

                        <p className="mt-7 text-center text-sm text-ink-faint">
                            {mode === 'verify' ? (
                                <>
                                    Didn&apos;t get it?{' '}
                                    <button
                                        type="button"
                                        onClick={resendCode}
                                        disabled={resendCooldown > 0}
                                        className="cursor-pointer text-accent transition-opacity duration-500 ease-fluid hover:opacity-70 disabled:cursor-not-allowed disabled:opacity-40"
                                    >
                                        {resendCooldown > 0 ? `Resend in ${resendCooldown}s` : 'Resend code'}
                                    </button>
                                </>
                            ) : (
                                <>
                                    {mode === 'signup' ? 'Already have an account?' : "Don't have an account?"}{' '}
                                    <button
                                        type="button"
                                        onClick={() => switchMode(mode === 'signup' ? 'signin' : 'signup')}
                                        className="cursor-pointer text-accent transition-opacity duration-500 ease-fluid hover:opacity-70"
                                    >
                                        {mode === 'signup' ? 'Sign in' : 'Create one'}
                                    </button>
                                </>
                            )}
                        </p>
                    </div>
                </PageFade>
            </div>
        </div>
    )
}

export default Login
