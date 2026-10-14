import { memo, useMemo, useState, useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { Menu, X, ChevronRight, ShieldCheck, Sun, Moon, Camera, LogOut } from 'lucide-react'
import { NAV_BY_ROLE, ROLE_LABELS } from '../app/navigation'

function ThemeToggle() {
  const [isDark, setIsDark] = useState(() => {
    const saved = localStorage.getItem('theme')
    if (saved) {
      const isDarkTheme = saved === 'dark'
      if (isDarkTheme) {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
      return isDarkTheme
    }
    return document.documentElement.classList.contains('dark')
  })

  useEffect(() => {
    const saved = localStorage.getItem('theme')
    if (saved) {
      setIsDark(saved === 'dark')
    } else {
      setIsDark(document.documentElement.classList.contains('dark'))
    }
  }, [])

  const toggleTheme = () => {
    const root = document.documentElement
    if (root.classList.contains('dark')) {
      root.classList.remove('dark')
      setIsDark(false)
      localStorage.setItem('theme', 'light')
    } else {
      root.classList.add('dark')
      setIsDark(true)
      localStorage.setItem('theme', 'dark')
    }
  }

  return (
    <button 
      onClick={toggleTheme}
      className="p-2 rounded-xl bg-elevated border border-border hover:bg-elevated/80 transition-all duration-300 flex items-center justify-center"
      aria-label="Toggle theme"
    >
      {isDark ? <Sun className="w-4 h-4 text-neon-amber" /> : <Moon className="w-4 h-4 text-muted" />}
    </button>
  )
}

const SideNavItem = memo(function SideNavItem({ item, onClick, index }) {
  const { path, icon: Icon, label, badge } = item

  return (
    <NavLink
      to={path}
      onClick={onClick}
      className={({ isActive }) =>
        `sidebar-link ${isActive ? 'active' : ''}`
      }
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <Icon className="w-[18px] h-[18px] shrink-0" weight="regular" />
      <span className="text-[13px] flex-1">{label}</span>
      {badge === 'hero' && (
        <span className="flex items-center gap-1 text-[9px] bg-neon-green/10 text-neon-green px-2 py-0.5 rounded-full font-semibold uppercase tracking-wider">
          <span className="w-1.5 h-1.5 rounded-full bg-neon-green animate-pulse" />
          Live
        </span>
      )}
      {!badge && (
        <ChevronRight className="w-3.5 h-3.5 text-muted/0 group-hover:text-muted transition-all opacity-0 group-hover:opacity-100" />
      )}
    </NavLink>
  )
})

const ROLE_ICONS = {
  constable: ShieldCheck,
  si: ShieldCheck,
  acp: ShieldCheck,
  scout: Camera,
}

export default function AppShell({ role, children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const location = useLocation()
  const navItems = useMemo(() => NAV_BY_ROLE[role] || NAV_BY_ROLE.acp, [role])

  useEffect(() => {
    setSidebarOpen(false)
    const main = document.querySelector('#main-scroll')
    if (main) {
      main.scrollTop = 0
    }
  }, [location.pathname])

  useEffect(() => {
    const main = document.querySelector('#main-scroll')
    if (!main) return
    const handler = () => setScrolled(main.scrollTop > 10)
    main.addEventListener('scroll', handler, { passive: true })
    return () => main.removeEventListener('scroll', handler)
  }, [])

  return (
    <div className="flex h-screen overflow-hidden bg-base grid-bg noise-overlay relative">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex flex-col w-[260px] bg-sidebar border-r border-border relative z-50">
        {/* Brand */}
        <div className="px-6 py-6 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-neon-green/10 flex items-center justify-center border border-neon-green/20">
              <img src="/app_logo.jpeg" alt="DispatchMind" className="w-6 h-6 object-contain" onError={(e) => {
                e.target.style.display = 'none'
                e.target.nextSibling.style.display = 'flex'
              }} />
              <div className="hidden items-center justify-center">
                <ShieldCheck className="w-5 h-5 text-neon-green" strokeWidth={1.5} />
              </div>
            </div>
            <div>
              <h1 className="font-heading font-bold text-[15px] text-chalk tracking-tight">
                DispatchMind
              </h1>
              <p className="text-[10px] text-muted uppercase tracking-[0.2em]">
                BTP Co-Pilot
              </p>
            </div>
          </div>
        </div>

        {/* Current Role */}
        <div className="px-5 py-4 border-b border-border">
          <label className="text-[10px] uppercase tracking-[0.2em] text-muted/60 font-semibold mb-2 block">
            Role
          </label>
          <div className="input-glass text-xs py-2 text-chalk font-medium">
            {ROLE_LABELS[role] || role}
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {navItems.map((item, i) => (
            <div key={`${role}-${item.path}`} className="group">
              <SideNavItem item={item} index={i} />
            </div>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-5 py-5 border-t border-border flex flex-col gap-3">
          <button
            onClick={() => {
              localStorage.removeItem("token");
              localStorage.removeItem("user");
              window.location.reload();
            }}
            className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded-xl border border-border/80 bg-elevated/40 hover:bg-signal-red/10 hover:border-signal-red/20 text-xs text-muted hover:text-signal-red transition-all duration-300 font-medium cursor-pointer animate-in fade-in duration-300"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
          <div className="flex items-center justify-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-neon-green animate-pulse" />
            <p className="text-[10px] text-muted/40 uppercase tracking-[0.2em] font-medium">
              Gridlock Hackathon 2.0
            </p>
          </div>
        </div>
      </aside>

      {/* Mobile Sidebar Overlay */}
      <div
        className={`fixed inset-0 bg-black/80 backdrop-blur-xl z-40 lg:hidden transition-opacity duration-300 ${
          sidebarOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={() => setSidebarOpen(false)}
      />

      {/* Mobile Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-[280px] bg-sidebar border-r border-border flex flex-col
          transform transition-transform duration-300 ease-out lg:hidden
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}
      >
        <div className="px-6 py-6 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-2xl bg-neon-green/10 flex items-center justify-center border border-neon-green/20 overflow-hidden">
              <img src="/app_logo.jpeg" alt="DispatchMind" className="w-7 h-7 object-contain" onError={(e) => {
                e.target.style.display = 'none'
                e.target.nextSibling.style.display = 'flex'
              }} />
              <div className="hidden items-center justify-center">
                <ShieldCheck className="w-5 h-5 text-neon-green" strokeWidth={1.5} />
              </div>
            </div>
            <div>
              <h1 className="font-heading font-bold text-sm text-chalk">DispatchMind</h1>
              <p className="text-[9px] text-muted uppercase tracking-[0.2em]">BTP Co-Pilot</p>
            </div>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="p-2 rounded-xl hover:bg-black/5 dark:hover:bg-white/[0.05] transition-colors"
          >
            <X className="w-5 h-5 text-muted" />
          </button>
        </div>

        <div className="px-5 py-4 border-b border-border">
          <label className="text-[10px] uppercase tracking-[0.2em] text-muted/60 font-semibold mb-2 block">
            Role
          </label>
          <div className="input-glass text-xs py-2 text-chalk font-medium">
            {ROLE_LABELS[role] || role}
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {navItems.map((item, i) => (
            <div key={`${role}-${item.path}`} className="group">
              <SideNavItem item={item} onClick={() => setSidebarOpen(false)} index={i} />
            </div>
          ))}
        </nav>

        <div className="px-5 py-5 border-t border-border mt-auto">
          <button
            onClick={() => {
              localStorage.removeItem("token");
              localStorage.removeItem("user");
              window.location.reload();
            }}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl border border-border/80 bg-elevated/40 hover:bg-signal-red/10 hover:border-signal-red/20 text-xs text-muted hover:text-signal-red transition-all duration-300 font-medium cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden bg-base">
        {/* Header */}
        <div className={`flex items-center justify-between px-4 lg:px-8 py-3 border-b border-border bg-sidebar/80 backdrop-blur-xl sticky top-0 z-30 transition-shadow duration-300 ${scrolled ? 'shadow-lg' : ''}`}>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 rounded-xl hover:bg-black/5 dark:hover:bg-white/[0.05] transition-colors"
              aria-label="Open navigation menu"
            >
              <Menu className="w-5 h-5 text-chalk" />
            </button>
            <div className="lg:hidden flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-xl bg-neon-green/10 flex items-center justify-center border border-neon-green/20 overflow-hidden">
                <img src="/app_logo.jpeg" alt="DispatchMind" className="w-5 h-5 object-contain" onError={(e) => {
                  e.target.style.display = 'none'
                  e.target.nextSibling.style.display = 'flex'
                }} />
                <div className="hidden items-center justify-center">
                  <ShieldCheck className="w-3.5 h-3.5 text-neon-green" strokeWidth={1.5} />
                </div>
              </div>
              <h1 className="font-heading font-bold text-sm text-chalk tracking-tight">DispatchMind</h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
          </div>
        </div>

        {/* Page Content */}
        <div
          id="main-scroll"
          className="flex-1 overflow-y-auto"
        >
          <div 
            key={location.pathname}
            className="p-4 lg:p-8 xl:p-10 max-w-[1400px] mx-auto page-transition-fade"
          >
            {children}
          </div>
        </div>
      </main>
    </div>
  )
}
