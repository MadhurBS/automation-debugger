import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Eye, EyeOff, Loader2, ArrowRight } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'

const FEATURES = [
  'Auto-detect UiPath, Power Automate, Blue Prism & AA',
  'AI-powered root cause analysis',
  'Coding standards checker — 23 rules',
  'PDF & Excel RCA reports',
  'Team collaboration & audit history',
]

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login, register } = useAuthStore()
  const [tab, setTab]               = useState<'login' | 'register'>('login')
  const [loading, setLoading]       = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [form, setForm]             = useState({ email: '', password: '', fullName: '' })

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/dashboard'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      if (tab === 'login') {
        await login(form.email, form.password)
        navigate(from, { replace: true })
      } else {
        await register(form.email, form.fullName, form.password)
        toast.success('Account created — please sign in.')
        setTab('login')
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'An error occurred'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex font-sans">

      {/* ── LEFT — IBM brand panel — Carbon White uses IBM Blue fill ──── */}
      <div className="hidden lg:flex flex-col justify-between w-[45%] bg-ibm-blue60 px-14 py-12">

        {/* IBM wordmark + product */}
        <div>
          {/* IBM 8-bar SVG logo */}
          <svg width="60" height="24" viewBox="0 0 80 32" fill="none" className="mb-6">
            <rect y="0"  width="80" height="5" fill="#0f62fe"/>
            <rect y="7"  width="60" height="5" fill="#0f62fe"/>
            <rect y="7"  x="70" width="10" height="5" fill="#0f62fe"/>
            <rect y="14" width="60" height="5" fill="#0f62fe"/>
            <rect y="14" x="70" width="10" height="5" fill="#0f62fe"/>
            <rect y="21" width="60" height="5" fill="#0f62fe"/>
            <rect y="27" width="80" height="5" fill="#0f62fe"/>
          </svg>

          <h1 className="text-4xl font-light text-white leading-snug mb-2">
            RPA Automation<br />
            <span className="font-semibold">Debugger</span>
          </h1>
          <p className="text-ibm-blue20 text-sm font-light leading-relaxed mt-4 max-w-xs">
            AI-powered failure analysis for enterprise RPA platforms — built on IBM design standards.
          </p>
        </div>

        {/* Feature list */}
        <div className="space-y-3">
          <p className="text-2xs font-semibold uppercase tracking-widest text-ibm-blue20 mb-4 opacity-80">
            What's included
          </p>
          {FEATURES.map(f => (
            <div key={f} className="flex items-start gap-3">
              {/* White checkmark box on blue */}
              <span className="mt-0.5 w-4 h-4 bg-white/20 flex items-center justify-center flex-shrink-0">
                <svg viewBox="0 0 12 12" width="10" height="10" fill="none">
                  <polyline points="1,6 4.5,10 11,2" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </span>
              <span className="text-white text-sm font-light leading-tight">{f}</span>
            </div>
          ))}
        </div>

        {/* Footer */}
        <p className="text-ibm-blue20 text-2xs opacity-70">
          © {new Date().getFullYear()} IBM Corporation. All rights reserved.
        </p>
      </div>

      {/* ── RIGHT — form panel — pure white ───────────────────────────── */}
      <div className="flex-1 flex items-center justify-center bg-white px-6">
        <div className="w-full max-w-sm">

          {/* Mobile IBM mark */}
          <div className="lg:hidden mb-8">
            <svg width="48" height="20" viewBox="0 0 80 32" fill="none">
              <rect y="0"  width="80" height="5" fill="#0f62fe"/>
              <rect y="7"  width="60" height="5" fill="#0f62fe"/>
              <rect y="7"  x="70" width="10" height="5" fill="#0f62fe"/>
              <rect y="14" width="60" height="5" fill="#0f62fe"/>
              <rect y="14" x="70" width="10" height="5" fill="#0f62fe"/>
              <rect y="21" width="60" height="5" fill="#0f62fe"/>
              <rect y="27" width="80" height="5" fill="#0f62fe"/>
            </svg>
            <p className="mt-2 text-carbon-100 text-sm font-medium">RPA Automation Debugger</p>
          </div>

          <h2 className="text-2xl font-semibold text-carbon-100 mb-1">
            {tab === 'login' ? 'Sign in' : 'Create account'}
          </h2>
          <p className="text-carbon-60 text-sm mb-8">
            {tab === 'login' ? 'Use your IBM account or registered email' : 'Fill in your details to get started'}
          </p>

          {/* Tab switcher — Carbon style */}
          <div className="flex border-b border-carbon-20 mb-6">
            {(['login', 'register'] as const).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={[
                  'px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px',
                  tab === t
                    ? 'border-ibm-blue60 text-ibm-blue60'
                    : 'border-transparent text-carbon-60 hover:text-carbon-100',
                ].join(' ')}
              >
                {t === 'login' ? 'Sign In' : 'Register'}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {tab === 'register' && (
              <div>
                <label className="block text-xs font-medium text-carbon-70 mb-1">Full Name</label>
                <input
                  className="input"
                  placeholder="e.g. Jane Smith"
                  value={form.fullName}
                  onChange={e => setForm(f => ({ ...f, fullName: e.target.value }))}
                  required
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-carbon-70 mb-1">Email address</label>
              <input
                type="email"
                className="input"
                placeholder="you@company.com"
                value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-carbon-70 mb-1">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  className="input pr-10"
                  placeholder={tab === 'register' ? 'Min 8 chars, 1 uppercase, 1 digit' : 'Enter password'}
                  value={form.password}
                  onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-carbon-40 hover:text-carbon-70"
                >
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {/* Carbon primary button — full width */}
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full justify-between mt-2"
            >
              <span>{tab === 'login' ? 'Sign in' : 'Create account'}</span>
              {loading
                ? <Loader2 size={16} className="animate-spin" />
                : <ArrowRight size={16} />
              }
            </button>
          </form>

          <p className="mt-8 text-2xs text-carbon-50 leading-relaxed">
            By signing in you agree to IBM's terms of use and privacy policy.
          </p>
        </div>
      </div>

    </div>
  )
}
