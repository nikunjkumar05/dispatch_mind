import { useState, lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { 
  Shield, Map, AlertTriangle, Route as RouteIcon, 
  Users, BarChart3, Menu
} from 'lucide-react'

const Overview = lazy(() => import('./pages/Overview'))
const PriorityQueue = lazy(() => import('./pages/PriorityQueue'))
const MapView = lazy(() => import('./pages/MapView'))
const Cascade = lazy(() => import('./pages/Cascade'))
const Dispatch = lazy(() => import('./pages/Dispatch'))
const Alerts = lazy(() => import('./pages/Alerts'))
const RepeatOffenders = lazy(() => import('./pages/RepeatOffenders'))

const NAV_ITEMS = [
  { path: '/', icon: BarChart3, label: 'Overview' },
  { path: '/priority', icon: AlertTriangle, label: 'Priority Queue' },
  { path: '/map', icon: Map, label: 'Map View' },
  { path: '/cascade', icon: RouteIcon, label: 'Cascade Proof' },
  { path: '/dispatch', icon: Shield, label: 'Dispatch Plan' },
  { path: '/alerts', icon: AlertTriangle, label: 'Alerts' },
  { path: '/offenders', icon: Users, label: 'Repeat Offenders' },
]

function PageLoader() {
  return (
    <div className="flex items-center justify-center h-[60vh]">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-khaki/30 border-t-khaki rounded-full animate-spin" />
        <p className="text-mist/50 text-sm">Loading...</p>
      </div>
    </div>
  )
}

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [role, setRole] = useState('constable')

  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden">
        {/* Sidebar */}
        <aside className={`
          fixed inset-y-0 left-0 z-50 w-64 bg-asphalt border-r border-mist/10
          transform transition-transform duration-200 ease-in-out
          lg:relative lg:translate-x-0
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}>
          <div className="flex items-center gap-3 px-6 py-4 border-b border-mist/10">
            <div className="w-10 h-10 bg-khaki rounded-lg flex items-center justify-center">
              <Shield className="w-6 h-6 text-asphalt" />
            </div>
            <div>
              <h1 className="font-heading font-bold text-lg text-chalk leading-tight">DispatchMind</h1>
              <p className="text-xs text-mist/50">BTP Co-Pilot</p>
            </div>
          </div>

          {/* Role Selector */}
          <div className="px-4 py-3 border-b border-mist/10">
            <label className="text-xs uppercase tracking-wider text-mist/40 font-semibold">Role</label>
            <select 
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="mt-1 w-full bg-stone/50 border border-mist/20 rounded-lg px-3 py-2 text-sm text-chalk focus:outline-none focus:border-khaki"
            >
              <option value="constable">Constable (On Beat)</option>
              <option value="si">Sub-Inspector (Station)</option>
              <option value="acp">ACP / Commissioner</option>
            </select>
          </div>

          {/* Navigation */}
          <nav className="px-3 py-4 space-y-1">
            {NAV_ITEMS.map(({ path, icon: Icon, label }) => (
              <NavLink
                key={path}
                to={path}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) => `
                  sidebar-link ${isActive ? 'active' : ''}
                `}
              >
                <Icon className="w-5 h-5" />
                <span className="text-sm">{label}</span>
              </NavLink>
            ))}
          </nav>

          {/* Footer */}
          <div className="absolute bottom-0 left-0 right-0 px-4 py-3 border-t border-mist/10">
            <p className="text-xs text-mist/30 text-center">
              Gridlock Hackathon 2.0
            </p>
          </div>
        </aside>

        {/* Overlay */}
        {sidebarOpen && (
          <div 
            className="fixed inset-0 bg-black/50 z-40 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto">
          {/* Mobile Header */}
          <div className="lg:hidden flex items-center gap-3 px-4 py-3 border-b border-mist/10 bg-asphalt sticky top-0 z-30">
            <button 
              onClick={() => setSidebarOpen(true)}
              className="p-2 rounded-lg hover:bg-stone/50 transition-colors"
            >
              <Menu className="w-5 h-5 text-chalk" />
            </button>
            <h1 className="font-heading font-bold text-chalk">DispatchMind</h1>
          </div>

          <div className="p-4 lg:p-6 max-w-7xl mx-auto">
            <Suspense fallback={<PageLoader />}>
              <Routes>
                <Route path="/" element={<Overview />} />
                <Route path="/priority" element={<PriorityQueue role={role} />} />
                <Route path="/map" element={<MapView />} />
                <Route path="/cascade" element={<Cascade />} />
                <Route path="/dispatch" element={<Dispatch />} />
                <Route path="/alerts" element={<Alerts />} />
                <Route path="/offenders" element={<RepeatOffenders />} />
              </Routes>
            </Suspense>
          </div>
        </main>
      </div>
    </BrowserRouter>
  )
}
