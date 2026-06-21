import { useState, lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { 
  Shield, Map, AlertTriangle, Route as RouteIcon, 
  Users, BarChart3, Menu, Zap, Target, Activity, Radio,
  Smartphone, ClipboardList, Briefcase
} from 'lucide-react'

const Overview = lazy(() => import('./pages/Overview'))
const PriorityQueue = lazy(() => import('./pages/PriorityQueue'))
const MapView = lazy(() => import('./pages/MapView'))
const Cascade = lazy(() => import('./pages/Cascade'))
const Dispatch = lazy(() => import('./pages/Dispatch'))
const Alerts = lazy(() => import('./pages/Alerts'))
const ImpactCalculator = lazy(() => import('./pages/ImpactCalculator'))
const EarlyWarningPanel = lazy(() => import('./pages/EarlyWarningPanel'))
const Simulator = lazy(() => import('./pages/Simulator'))
const RepeatOffenders = lazy(() => import('./pages/RepeatOffenders'))

// Role-based navigation configuration
const ROLE_CONFIG = {
  constable: {
    name: 'Constable',
    subtitle: 'On Beat',
    icon: Smartphone,
    color: 'from-emerald-500 to-teal-600',
    accentColor: '#22C55E',
    navItems: [
      { path: '/', icon: Target, label: 'My Beat Impact', badge: 'live' },
      { path: '/alerts', icon: Zap, label: 'Live Alerts', badge: 'urgent' },
      { path: '/map', icon: Map, label: 'Tactical Map' },
      { path: '/dispatch', icon: RouteIcon, label: 'Clearance Route' },
      { path: '/priority', icon: AlertTriangle, label: 'Quick Actions' },
    ],
    quickActions: ['Report Clearance', 'Request Backup', 'Log Violation']
  },
  si: {
    name: 'Sub-Inspector',
    subtitle: 'Station Command',
    icon: ClipboardList,
    color: 'from-blue-500 to-indigo-600',
    accentColor: '#3B82F6',
    navItems: [
      { path: '/', icon: BarChart3, label: 'Station Dashboard' },
      { path: '/early-warning', icon: Radio, label: 'Early Warning', badge: 'new' },
      { path: '/priority', icon: AlertTriangle, label: 'Resource Allocation' },
      { path: '/dispatch', icon: Shield, label: 'Team Dispatch' },
      { path: '/map', icon: Map, label: 'Coverage Map' },
      { path: '/cascade', icon: RouteIcon, label: 'Cascade Analysis' },
      { path: '/repeat-offenders', icon: Users, label: 'Repeat Offenders' },
    ],
    quickActions: ['Deploy Team', 'Generate Report', 'Escalate Issue']
  },
  acp: {
    name: 'ACP / Commissioner',
    subtitle: 'City Command',
    icon: Briefcase,
    color: 'from-purple-500 to-pink-600',
    accentColor: '#A855F7',
    navItems: [
      { path: '/', icon: Target, label: 'City Overview', badge: 'hero' },
      { path: '/early-warning', icon: Radio, label: 'City Pulse', badge: 'new' },
      { path: '/simulator', icon: Activity, label: 'Policy Simulator' },
      { path: '/map', icon: Map, label: 'Strategic Map' },
      { path: '/cascade', icon: RouteIcon, label: 'Congestion Proof' },
      { path: '/impact', icon: BarChart3, label: 'Impact Analytics' },
    ],
    quickActions: ['Issue Advisory', 'Request Budget', 'Multi-Agency Meet']
  }
}

const NAV_ITEMS = [
  { path: '/', icon: Target, label: 'Impact Dashboard', badge: 'hero' },
  { path: '/early-warning', icon: Radio, label: 'Early Warning', badge: 'new' },
  { path: '/priority', icon: AlertTriangle, label: 'Action Plan' },
  { path: '/dispatch', icon: Shield, label: 'Dispatch Routes' },
  { path: '/map', icon: Map, label: 'Tactical Map' },
  { path: '/cascade', icon: RouteIcon, label: 'Cascade Proof' },
  { path: '/alerts', icon: Zap, label: 'Live Alerts' },
  { path: '/simulator', icon: Activity, label: 'Simulator' },
  { path: '/repeat-offenders', icon: Users, label: 'Repeat Offenders' },
]

function PageLoader() {
  return (
    <div className="flex items-center justify-center h-[60vh]">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
        <p className="text-muted text-sm">Loading...</p>
      </div>
    </div>
  )
}

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [role, setRole] = useState('constable')
  
  const currentRole = ROLE_CONFIG[role] || ROLE_CONFIG.constable
  const RoleIcon = currentRole.icon

  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden bg-base">
        {/* Sidebar */}
        <aside className={`
          fixed inset-y-0 left-0 z-50 w-64 bg-sidebar border-r border-white/[0.06]
          transform transition-transform duration-300 ease-out
          lg:relative lg:translate-x-0
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}>
          {/* Logo with Role Badge */}
          <div className="relative overflow-hidden">
            <div className={`absolute inset-0 bg-gradient-to-r ${currentRole.color} opacity-10`} />
            <div className="flex items-center gap-3 px-5 py-5 border-b border-white/[0.06] relative">
              <div className={`w-10 h-10 bg-gradient-to-br ${currentRole.color} rounded-xl flex items-center justify-center shadow-lg`}>
                <RoleIcon className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="font-heading font-bold text-base text-chalk leading-tight">DispatchMind</h1>
                <p className="text-[10px] text-muted uppercase tracking-wider">BTP Co-Pilot</p>
              </div>
            </div>
            {/* Role Indicator Strip */}
            <div className={`h-1 bg-gradient-to-r ${currentRole.color}`} />
          </div>

          {/* Role Selector */}
          <div className="px-4 py-4 border-b border-white/[0.06]">
            <label className="text-[10px] uppercase tracking-wider text-muted font-medium mb-2 block">
              Operating As
            </label>
            <div className="grid grid-cols-3 gap-2">
              {Object.entries(ROLE_CONFIG).map(([key, config]) => {
                const Icon = config.icon
                const isActive = key === role
                return (
                  <button
                    key={key}
                    onClick={() => setRole(key)}
                    className={`
                      flex flex-col items-center gap-1 p-2 rounded-lg border transition-all duration-200
                      ${isActive 
                        ? `bg-gradient-to-br ${config.color} border-transparent text-white shadow-lg` 
                        : 'bg-elevated border-white/[0.08] text-muted hover:bg-elevated/80 hover:border-white/[0.15]'
                      }
                    `}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="text-[9px] font-medium">{config.name.split(' ')[0]}</span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="px-4 py-3 border-b border-white/[0.06]">
            <label className="text-[10px] uppercase tracking-wider text-muted font-medium mb-2 block">
              Quick Actions
            </label>
            <div className="space-y-1.5">
              {currentRole.quickActions.map((action, idx) => (
                <button
                  key={idx}
                  className="w-full text-left px-3 py-2 text-xs text-chalk bg-elevated/50 hover:bg-elevated rounded-lg transition-colors border border-white/[0.06] hover:border-accent/30"
                >
                  {action}
                </button>
              ))}
            </div>
          </div>

          {/* Navigation */}
          <nav className="px-3 py-3 space-y-1 flex-1 overflow-y-auto">
            {currentRole.navItems.map(({ path, icon: Icon, label, badge }) => (
              <NavLink
                key={path}
                to={path}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) => `
                  sidebar-link ${isActive ? 'active' : ''}
                  ${badge === 'live' ? 'border-l-2 border-signal-emerald animate-pulse-subtle' : ''}
                  ${badge === 'hero' ? 'border-l-2 border-signal-emerald' : ''}
                  ${badge === 'urgent' ? 'border-l-2 border-signal-red' : ''}
                  ${badge === 'new' ? 'border-l-2 border-accent' : ''}
                `}
              >
                <Icon className="w-4 h-4" />
                <span className="text-sm">{label}</span>
                {badge && (
                  <span className={`ml-auto text-[9px] px-1.5 py-0.5 rounded font-medium ${
                    badge === 'live' ? 'bg-signal-emerald/20 text-signal-emerald animate-pulse' :
                    badge === 'urgent' ? 'bg-signal-red/20 text-signal-red' :
                    badge === 'hero' ? 'bg-signal-emerald/20 text-signal-emerald' :
                    badge === 'new' ? 'bg-accent/20 text-accent' :
                    'bg-elevated text-muted'
                  }`}>
                    {badge.toUpperCase()}
                  </span>
                )}
              </NavLink>
            ))}
          </nav>

          {/* Footer */}
          <div className="absolute bottom-0 left-0 right-0 px-4 py-3 border-t border-white/[0.06] bg-sidebar/50 backdrop-blur-sm">
            <div className="flex items-center justify-between">
              <p className="text-[9px] text-muted/60 uppercase tracking-wider">
                Gridlock Hackathon 2.0
              </p>
              <div className={`w-2 h-2 rounded-full bg-gradient-to-r ${currentRole.color} animate-pulse`} />
            </div>
          </div>
        </aside>

        {/* Overlay */}
        {sidebarOpen && (
          <div 
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto bg-base">
          {/* Mobile Header */}
          <div className="lg:hidden flex items-center gap-3 px-4 py-3 border-b border-white/[0.06] bg-sidebar sticky top-0 z-30">
            <button 
              onClick={() => setSidebarOpen(true)}
              className="p-2 rounded-lg hover:bg-elevated transition-colors"
            >
              <Menu className="w-5 h-5 text-chalk" />
            </button>
            <div className={`w-8 h-8 bg-gradient-to-br ${currentRole.color} rounded-lg flex items-center justify-center`}>
              <RoleIcon className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="font-heading font-bold text-sm text-chalk">DispatchMind</h1>
              <p className="text-[9px] text-muted">{currentRole.subtitle}</p>
            </div>
          </div>

          {/* Role Banner for Desktop */}
          <div className="hidden lg:block border-b border-white/[0.06] bg-sidebar/30">
            <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 bg-gradient-to-br ${currentRole.color} rounded-lg flex items-center justify-center`}>
                  <RoleIcon className="w-4 h-4 text-white" />
                </div>
                <div>
                  <h2 className="font-heading font-semibold text-sm text-chalk">{currentRole.name}</h2>
                  <p className="text-[10px] text-muted">{currentRole.subtitle}</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-signal-emerald animate-pulse" />
                  <span className="text-xs text-muted">System Online</span>
                </div>
                <div className="text-xs text-muted font-mono">
                  {new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            </div>
          </div>

          <div className="p-4 lg:p-6 max-w-7xl mx-auto">
            <Suspense fallback={<PageLoader />}>
              <Routes>
                <Route path="/" element={<ImpactCalculator role={role} />} />
                <Route path="/early-warning" element={<EarlyWarningPanel role={role} />} />
                <Route path="/overview" element={<Overview role={role} />} />
                <Route path="/priority" element={<PriorityQueue role={role} />} />
                <Route path="/map" element={<MapView role={role} />} />
                <Route path="/cascade" element={<Cascade role={role} />} />
                <Route path="/dispatch" element={<Dispatch role={role} />} />
                <Route path="/alerts" element={<Alerts role={role} />} />
                <Route path="/simulator" element={<Simulator role={role} />} />
                <Route path="/repeat-offenders" element={<RepeatOffenders role={role} />} />
              </Routes>
            </Suspense>
          </div>
        </main>
      </div>
    </BrowserRouter>
  )
}
