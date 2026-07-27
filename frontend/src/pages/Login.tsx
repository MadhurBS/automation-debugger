import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Bug, Eye, EyeOff, Loader2 } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login, register } = useAuthStore()
  const [tab, setTab] = useState<'login' | 'register'>('login')
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [form, setForm] = useState({ email: '', password: '', fullName: '' })

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
        toast.success('Account created! Please log in.')
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
    <div className="min-h-screen flex">
      {/* Left branding panel */}
      <div className="hidden lg:flex flex-col justify-between w-1/2 bg-sidebar-bg p-12">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-primary-600 rounded-xl flex items-center justify-center">
            <Bug size={18} className="text-white" />
          </div>
          <span className="text-white font-semibold text-lg">RPA Debugger</span>
        </div>
        <div>
          <h1 className="text-4xl font-bold text-white leading-tight mb-4">
            AI-Powered<br />Automation<br />Debugger
          </h1>
          <p className="text-slate-400 text-base leading-relaxed mb-8">
            Automatically identify root causes of RPA automation failures across
            UiPath, Power Automate, Blue Prism, and Automation Anywhere.
          </p>
          <div className="space-y-3">
            {['Upload project ZIP or log files', 'AI-powered root cause analysis', 'Detailed RCA reports (PDF & Excel)', 'Team collaboration & history'].map(f => (
              <div key={f} className="flex items-center gap-2.5">
                <div className="w-5 h-5 rounded-full bg-primary-600/30 flex items-center justify-center flex-shrink-0">
                  <div className="w-2 h-2 rounded-full bg-primary-400" />
                </div>
                <span className="text-slate-300 text-sm">{f}</span>
              </div>
            ))}
          </div>
        </div>
        <p className="text-slate-600 text-xs">© 2025 Automation Project Debugger</p>
      </div>

      {/* Right form panel */}
      <div className="flex-1 flex items-center justify-center p-6 bg-surface-1">
        <div className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-2 mb-8">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <Bug size={15} className="text-white" />
            </div>
            <span className="font-semibold text-gray-900">RPA Debugger</span>
          </div>

          <h2 className="text-2xl font-bold text-gray-900 mb-1">
            {tab === 'login' ? 'Welcome back' : 'Create account'}
          </h2>
          <p className="text-gray-500 text-sm mb-8">
            {tab === 'login' ? 'Sign in to your account' : 'Get started for free'}
          </p>

          {/* Tabs */}
          <div className="flex bg-gray-100 rounded-lg p-1 mb-6">
            {(['login', 'register'] as const).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-all ${
                  tab === t ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {t === 'login' ? 'Sign In' : 'Register'}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {tab === 'register' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
                <input
                  className="input"
                  placeholder="John Smith"
                  value={form.fullName}
                  onChange={e => setForm(f => ({ ...f, fullName: e.target.value }))}
                  required
                />
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
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
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  className="input pr-10"
                  placeholder={tab === 'register' ? 'Min 8 chars, 1 uppercase, 1 digit' : 'Your password'}
                  value={form.password}
                  onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full justify-center py-2.5">
              {loading ? <Loader2 size={16} className="animate-spin" /> : null}
              {tab === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
