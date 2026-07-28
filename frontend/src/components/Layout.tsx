import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, Upload, FileText, History,
  LogOut, Menu, X, ChevronDown, User,
} from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import clsx from 'clsx'

const navItems = [
  { label: 'Dashboard',      icon: LayoutDashboard, path: '/dashboard' },
  { label: 'Upload Project', icon: Upload,           path: '/upload/project' },
  { label: 'Upload Logs',    icon: FileText,         path: '/upload/log' },
  { label: 'History',        icon: History,          path: '/history' },
]

export default function Layout() {
  const navigate    = useNavigate()
  const location    = useLocation()
  const { user, logout } = useAuthStore()
  const [drawerOpen,  setDrawerOpen]  = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)

  const handleLogout = () => { logout(); navigate('/login') }

  const activeLabel = navItems.find(n => location.pathname.startsWith(n.path))?.label ?? 'Automation Debugger'

  /* ── Shared nav item renderer ── */
  const NavItem = ({ item }: { item: typeof navItems[0] }) => {
    const active = location.pathname.startsWith(item.path)
    return (
      <button
        onClick={() => { navigate(item.path); setDrawerOpen(false) }}
        className={clsx('shell-link', active ? 'shell-link-active' : 'shell-link-inactive')}
      >
        {/* Carbon left-border active indicator */}
        <span className={clsx(
          'absolute left-0 top-0 h-full w-0.5 transition-colors',
          active ? 'bg-ibm-blue40' : 'bg-transparent'
        )} />
        <item.icon size={16} className="flex-shrink-0" />
        <span>{item.label}</span>
      </button>
    )
  }

  /* ── Left nav panel ── */
  const LeftNav = () => (
    <div className="flex flex-col h-full w-64 bg-shell-bg">
      {/* Product name — Carbon "Header name" pattern */}
      <div className="flex items-center gap-0 h-12 px-4 border-b border-shell-border flex-shrink-0 bg-ibm-blue60">
        {/* IBM 8-bar logo mark in SVG */}
        <svg width="20" height="20" viewBox="0 0 32 32" fill="none" className="mr-3 flex-shrink-0">
          <rect y="4"  width="32" height="4" fill="#0f62fe"/>
          <rect y="10" width="24" height="4" fill="#0f62fe"/>
          <rect y="10" x="28" width="4" height="4" fill="#0f62fe"/>
          <rect y="16" width="24" height="4" fill="#0f62fe"/>
          <rect y="16" x="28" width="4" height="4" fill="#0f62fe"/>
          <rect y="22" width="24" height="4" fill="#0f62fe"/>
          <rect y="28" width="32" height="4" fill="#0f62fe"/>
        </svg>
        <span className="text-white text-sm font-semibold leading-none">RPA</span>
        <span className="text-ibm-blue20 text-sm font-light leading-none ml-1">Debugger</span>
      </div>

      {/* Section label */}
      <div className="px-4 pt-4 pb-1 border-b border-shell-border mb-1">
        <p className="text-2xs font-semibold uppercase tracking-widest text-carbon-50">Navigation</p>
      </div>

      {/* Nav links */}
      <nav className="flex-1 py-1 overflow-y-auto relative">
        {navItems.map(item => (
          <div key={item.path} className="relative">
            <NavItem item={item} />
          </div>
        ))}
      </nav>

      {/* User row */}
      <div className="border-t border-shell-border px-4 py-3 flex items-center gap-3 bg-carbon-10">
        <div className="w-7 h-7 bg-ibm-blue60 flex items-center justify-center flex-shrink-0">
          <User size={13} className="text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-carbon-100 text-xs font-medium truncate leading-tight">{user?.full_name}</p>
          <p className="text-carbon-60 text-2xs truncate">{user?.role}</p>
        </div>
        <button
          onClick={handleLogout}
          title="Sign out"
          className="text-carbon-50 hover:text-severity-critical transition-colors"
        >
          <LogOut size={14} />
        </button>
      </div>
    </div>
  )

  return (
    <div className="flex h-screen overflow-hidden bg-carbon-10">

      {/* ── Desktop left nav ── */}
      <aside className="hidden lg:flex flex-col flex-shrink-0 w-64 bg-shell-bg">
        <LeftNav />
      </aside>

      {/* ── Mobile drawer overlay ── */}
      {drawerOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div className="fixed inset-0 bg-black/60" onClick={() => setDrawerOpen(false)} />
          <aside className="relative z-10 flex flex-col flex-shrink-0 w-64 bg-shell-bg">
            <button
              onClick={() => setDrawerOpen(false)}
              className="absolute top-3 right-3 text-shell-text hover:text-white"
            >
              <X size={18} />
            </button>
            <LeftNav />
          </aside>
        </div>
      )}

      {/* ── Main area ── */}
      <div className="flex-1 flex flex-col overflow-hidden">

        {/* Carbon Global Header bar — white with bottom border + subtle shadow */}
        <header className="h-12 bg-shell-header border-b border-shell-border shadow-sm flex items-center justify-between px-4 flex-shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setDrawerOpen(true)}
              className="lg:hidden text-carbon-60 hover:text-carbon-100 p-1"
            >
              <Menu size={20} />
            </button>
            {/* Breadcrumb-style page title */}
            <span className="text-carbon-60 text-sm hidden sm:block">
              <span className="text-carbon-100 font-medium">{activeLabel}</span>
            </span>
          </div>

          {/* User menu */}
          <div className="relative">
            <button
              onClick={() => setUserMenuOpen(v => !v)}
              className="flex items-center gap-2 text-sm text-carbon-70 hover:text-carbon-100 transition-colors h-12 px-3"
            >
              <div className="w-6 h-6 bg-ibm-blue60 flex items-center justify-center">
                <User size={12} className="text-white" />
              </div>
              <span className="hidden sm:block text-xs">{user?.full_name}</span>
              <ChevronDown size={13} />
            </button>
            {userMenuOpen && (
              <div className="absolute right-0 top-full w-52 bg-white border border-carbon-20 shadow-card-md z-20 py-1">
                <div className="px-4 py-3 border-b border-carbon-20">
                  <p className="text-carbon-100 text-sm font-medium">{user?.full_name}</p>
                  <p className="text-carbon-60 text-xs mt-0.5">{user?.email}</p>
                </div>
                <button
                  onClick={() => { setUserMenuOpen(false); handleLogout() }}
                  className="flex items-center gap-2 w-full px-4 py-2.5 text-sm text-carbon-70 hover:bg-carbon-10 hover:text-carbon-100 transition-colors"
                >
                  <LogOut size={14} />
                  Sign out
                </button>
              </div>
            )}
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-5 lg:p-8">
          <Outlet />
        </main>

        {/* IBM footer strip */}
        <footer className="h-8 bg-carbon-10 border-t border-carbon-20 flex items-center px-4 flex-shrink-0">
          <span className="text-carbon-50 text-2xs">
            © {new Date().getFullYear()} IBM Corporation — RPA Automation Debugger
          </span>
        </footer>
      </div>
    </div>
  )
}
