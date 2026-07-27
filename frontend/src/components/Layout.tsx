import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, Upload, FileText, History, LogOut, Menu, X,
  Bug, ChevronDown, User,
} from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import clsx from 'clsx'

const navItems = [
  { label: 'Dashboard', icon: LayoutDashboard, path: '/dashboard' },
  { label: 'Upload Project', icon: Upload, path: '/upload/project' },
  { label: 'Upload Logs', icon: FileText, path: '/upload/log' },
  { label: 'History', icon: History, path: '/history' },
]

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)

  const handleLogout = async () => {
    logout()
    navigate('/login')
  }

  const Sidebar = ({ mobile = false }: { mobile?: boolean }) => (
    <div className={clsx(
      'flex flex-col h-full',
      mobile ? 'w-64' : 'w-64',
    )}>
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 py-5 border-b border-white/10">
        <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
          <Bug size={16} className="text-white" />
        </div>
        <div>
          <p className="text-white text-sm font-semibold leading-tight">RPA Debugger</p>
          <p className="text-sidebar-text text-xs">AI-Powered Analysis</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const active = location.pathname.startsWith(item.path)
          return (
            <button
              key={item.path}
              onClick={() => { navigate(item.path); setSidebarOpen(false) }}
              className={clsx('sidebar-link w-full', active ? 'sidebar-link-active' : 'sidebar-link-inactive')}
            >
              <item.icon size={16} />
              {item.label}
            </button>
          )
        })}
      </nav>

      {/* User */}
      <div className="px-3 py-4 border-t border-white/10">
        <div className="flex items-center gap-3 px-3 py-2 rounded-lg">
          <div className="w-8 h-8 bg-primary-700 rounded-full flex items-center justify-center">
            <User size={14} className="text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sidebar-textActive text-xs font-medium truncate">{user?.full_name}</p>
            <p className="text-sidebar-text text-xs truncate">{user?.role}</p>
          </div>
          <button onClick={handleLogout} className="text-sidebar-text hover:text-red-400 transition-colors">
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </div>
  )

  return (
    <div className="flex h-screen overflow-hidden bg-surface-1">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex flex-col bg-sidebar-bg w-64 flex-shrink-0">
        <Sidebar />
      </aside>

      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div className="fixed inset-0 bg-black/50" onClick={() => setSidebarOpen(false)} />
          <aside className="relative flex flex-col bg-sidebar-bg w-64 flex-shrink-0 z-10">
            <Sidebar mobile />
          </aside>
        </div>
      )}

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-1.5 text-gray-500 hover:text-gray-700"
            >
              <Menu size={20} />
            </button>
            <h1 className="text-base font-semibold text-gray-900 hidden sm:block">
              {navItems.find(n => location.pathname.startsWith(n.path))?.label ?? 'Automation Debugger'}
            </h1>
          </div>
          <div className="relative">
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
            >
              <div className="w-7 h-7 bg-primary-100 rounded-full flex items-center justify-center">
                <User size={13} className="text-primary-700" />
              </div>
              <span className="hidden sm:block">{user?.full_name}</span>
              <ChevronDown size={14} />
            </button>
            {userMenuOpen && (
              <div className="absolute right-0 top-full mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-10 py-1">
                <div className="px-3 py-2 border-b border-gray-100">
                  <p className="text-sm font-medium text-gray-900">{user?.full_name}</p>
                  <p className="text-xs text-gray-500">{user?.email}</p>
                </div>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 w-full px-3 py-2 text-sm text-red-600 hover:bg-red-50"
                >
                  <LogOut size={14} />
                  Sign out
                </button>
              </div>
            )}
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
