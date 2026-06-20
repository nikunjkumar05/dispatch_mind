import { useState, lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { 
  Shield, Map, AlertTriangle, Route as RouteIcon, 
  Users, BarChart3, Menu, Zap, Target, Activity, Radio
} from 'lucide-react'

const Overview = lazy(() => import('./pages/Overview'))
const PriorityQueue = lazy(() => import('./pages/PriorityQueue'))
const MapView = lazy(() => import('./pages/MapView'))
const Cascade = lazy(() => import('./pages/Cascade'))
const Dispatch = lazy(() => import('./pages/Dispatch'))
const Alerts = lazy(() => import('./pages/Alerts'))
const ImpactCalculator = lazy(() => import('./pages/ImpactCalculator'))
const EarlyWarningPanel = lazy(() => import('./pages/EarlyWarningPanel'))

const NAV_ITEMS = [
  { path: '/', icon: Target, label: 'Impact Dashboard', badge: 'hero' },
  { path: '/early-warning', icon: Radio, label: 'Early Warning', badge: 'new' },
  { path: '/priority', icon: AlertTriangle, label: 'Action Plan' },
  { path: '/dispatch', icon: Shield, label: 'Dispatch Routes' },
  { path: '/map', icon: Map, label: 'Tactical Map' },
  { path: '/cascade', icon: RouteIcon, label: 'Cascade Proof' },
  { path: '/alerts', icon: Zap, label: 'Live Alerts' },
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

  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden bg-base">
        {/* Sidebar */}
        <aside className={`
          fixed inset-y-0 left-0 z-50 w-60 bg-sidebar border-r border-white/[0.06]
          transform transition-transform duration-200 ease-in-out
          lg:relative lg:translate-x-0
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}>
          {/* Logo */}
          <div className="flex items-center gap-3 px-5 py-4 border-b border-white/[0.06]">
            <div className="w-9 h-9 bg-accent rounded-lg flex items-center justify-center shadow-glow-blue">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-heading font-bold text-base text-chalk leading-tight">DispatchMind</h1>
              <p className="text-[10px] text-muted uppercase tracking-wider">BTP Co-Pilot</p>
            </div>
          </div>

          {/* Role Selector */}
          <div className="px-4 py-3 border-b border-white/[0.06]">
            <label className="text-[10px] uppercase tracking-wider text-muted font-medium">Role</label>
            <select 
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="mt-1.5 w-full bg-elevated border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-chalk focus:outline-none focus:border-accent/50 transition-colors"
            >
              <option value="constable">Constable (On Beat)</option>
              <option value="si">Sub-Inspector (Station)</option>
              <option value="acp">ACP / Commissioner</option>
            </select>
          </div>

          {/* Navigation */}
          <nav className="px-3 py-3 space-y-0.5">
            {NAV_ITEMS.map(({ path, icon: Icon, label, badge }) => (
              <NavLink
                key={path}
                to={path}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) => `
                  sidebar-link ${isActive ? 'active' : ''}
                  ${badge === 'hero' ? 'border-l-2 border-signal-emerald' : ''}
                `}
              >
                <Icon className="w-4 h-4" />
                <span className="text-sm">{label}</span>
                {badge === 'hero' && (
                  <span className="ml-auto text-[9px] bg-signal-emerald/20 text-signal-emerald px-1.5 py-0.5 rounded font-medium">
                    LIVE
                  </span>
                )}
              </NavLink>
            ))}
          </nav>

          {/* Footer */}
          <div className="absolute bottom-0 left-0 right-0 px-4 py-3 border-t border-white/[0.06]">
            <p className="text-[10px] text-muted/60 text-center uppercase tracking-wider">
              Gridlock Hackathon 2.0
            </p>
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
            <h1 className="font-heading font-bold text-sm text-chalk">DispatchMind</h1>
          </div>

          <div className="p-4 lg:p-6 max-w-7xl mx-auto">
            <Suspense fallback={<PageLoader />}>
              <Routes>
                <Route path="/" element={<ImpactCalculator />} />
                <Route path="/early-warning" element={<EarlyWarningPanel />} />
                <Route path="/overview" element={<Overview />} />
                <Route path="/priority" element={<PriorityQueue role={role} />} />
                <Route path="/map" element={<MapView />} />
                <Route path="/cascade" element={<Cascade />} />
                <Route path="/dispatch" element={<Dispatch />} />
                <Route path="/alerts" element={<Alerts />} />
              </Routes>
            </Suspense>
          </div>
        </main>
      </div>
    </BrowserRouter>
  )
}
