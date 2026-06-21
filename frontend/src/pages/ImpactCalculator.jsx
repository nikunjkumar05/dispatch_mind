import { useState } from 'react'
import { useApi } from '../utils/api'
import { Target, TrendingDown, Users, Cloud, ArrowRight, Zap, CheckCircle, Clock, MapPin, Phone } from 'lucide-react'

const ROLE_THEMES = {
  constable: {
    primary: 'from-emerald-500 to-teal-600',
    accent: 'text-emerald-400',
    bgAccent: 'bg-emerald-500/10',
    borderAccent: 'border-emerald-500/20',
    gradientText: 'from-emerald-400 to-teal-400',
    icon: CheckCircle,
    title: 'My Beat Impact',
    subtitle: 'Real-time clearance impact tracking',
    quickStats: ['Clearances Today', 'Avg Recovery Time', 'Violations Logged']
  },
  si: {
    primary: 'from-blue-500 to-indigo-600',
    accent: 'text-blue-400',
    bgAccent: 'bg-blue-500/10',
    borderAccent: 'border-blue-500/20',
    gradientText: 'from-blue-400 to-indigo-400',
    icon: Clock,
    title: 'Station Dashboard',
    subtitle: 'Resource allocation & team performance',
    quickStats: ['Team Efficiency', 'Coverage Area', 'Response Time']
  },
  acp: {
    primary: 'from-purple-500 to-pink-600',
    accent: 'text-purple-400',
    bgAccent: 'bg-purple-500/10',
    borderAccent: 'border-purple-500/20',
    gradientText: 'from-purple-400 to-pink-400',
    icon: MapPin,
    title: 'City Overview',
    subtitle: 'Strategic congestion intelligence',
    quickStats: ['City-wide Impact', 'Hotspot Trends', 'Policy ROI']
  }
}

export default function ImpactCalculator({ role = 'constable' }) {
  const [selectedScenario, setSelectedScenario] = useState(5)
  const { data, loading } = useApi('/impact-summary')
  
  const theme = ROLE_THEMES[role] || ROLE_THEMES.constable
  const ThemeIcon = theme.icon

  if (loading) return <LoadingSkeleton />

  const total = data?.total || {}
  const scenarios = data?.scenarios || []
  const topJunctions = data?.top_junctions || []
  const activeScenario = scenarios.find(s => s.clear_count === selectedScenario)

  return (
    <div className="space-y-6">
      {/* Role-Specific Header with Gradient */}
      <div className={`relative overflow-hidden rounded-2xl p-6 bg-gradient-to-r ${theme.primary} bg-opacity-10`}>
        <div className="absolute inset-0 bg-black/20" />
        <div className="relative flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className={`w-12 h-12 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center`}>
              <ThemeIcon className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="font-heading font-bold text-2xl text-white flex items-center gap-2">
                {theme.title}
              </h1>
              <p className="text-white/80 text-sm mt-1">
                {theme.subtitle}
              </p>
            </div>
          </div>
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/20 backdrop-blur-sm">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs text-white font-medium">Live Data</span>
          </div>
        </div>
        
        {/* Quick Stats Row */}
        <div className="mt-6 grid grid-cols-3 gap-4">
          {theme.quickStats.map((stat, idx) => (
            <div key={idx} className="text-center">
              <p className="text-[10px] uppercase tracking-wider text-white/60">{stat}</p>
              <p className="text-lg font-bold text-white mt-0.5">
                {idx === 0 ? '--' : idx === 1 ? '--' : '--'}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Total Impact Banner */}
      <div className={`card border-2 ${theme.borderAccent} ${theme.bgAccent}`}>
        <p className={`text-xs uppercase tracking-wider ${theme.accent} font-semibold mb-4 flex items-center gap-2`}>
          <Zap className="w-4 h-4" />
          Current Total Impact (All Violations)
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard
            icon={<Zap className="w-5 h-5" />}
            label="Vehicles Blocked/hr"
            value={total.vehicles_blocked_hr?.toLocaleString() || '0'}
            color="text-signal-red"
            gradient={false}
          />
          <MetricCard
            icon={<TrendingDown className="w-5 h-5" />}
            label="Economic Loss/hr"
            value={`INR ${(total.economic_loss_inr || 0).toLocaleString()}`}
            color="text-signal-orange"
            gradient={false}
          />
          <MetricCard
            icon={<Users className="w-5 h-5" />}
            label="Person-Hours Blocked"
            value={(total.person_hours_blocked || 0).toLocaleString()}
            color="text-signal-amber"
            gradient={false}
          />
          <MetricCard
            icon={<Cloud className="w-5 h-5" />}
            label="CO2 Emissions (kg)"
            value={(total.co2_kg || 0).toLocaleString()}
            color="text-signal-emerald"
            gradient={false}
          />
        </div>
      </div>

      {/* Scenario Selector */}
      <div className="card">
        <h2 className="font-heading font-semibold text-lg text-chalk mb-4 flex items-center gap-2">
          <TrendingDown className="w-5 h-5 text-signal-emerald" />
          If You Clear Top N Junctions
        </h2>
        
        <div className="flex gap-2 mb-6">
          {[1, 3, 5, 10].map(n => (
            <button
              key={n}
              onClick={() => setSelectedScenario(n)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                selectedScenario === n
                  ? 'bg-signal-emerald text-white'
                  : 'bg-elevated text-muted hover:bg-elevated/80'
              }`}
            >
              Top {n}
            </button>
          ))}
        </div>

        {activeScenario && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Impact Summary */}
            <div className="space-y-4">
              <div className="p-4 bg-elevated rounded-xl">
                <p className="text-xs text-muted uppercase tracking-wider mb-2">Impact Saved</p>
                <div className="space-y-2">
                  <ImpactRow
                    label="Vehicles/hr freed"
                    value={activeScenario.vehicles_saved_hr?.toLocaleString()}
                    pct={activeScenario.pct_of_total_impact}
                  />
                  <ImpactRow
                    label="Economic savings/hr"
                    value={`INR ${activeScenario.economic_savings_inr?.toLocaleString()}`}
                    pct={activeScenario.pct_of_total_impact}
                  />
                  <ImpactRow
                    label="Person-hours saved"
                    value={activeScenario.person_hours_saved?.toLocaleString()}
                  />
                  <ImpactRow
                    label="CO2 reduction"
                    value={`${activeScenario.co2_saved_kg?.toLocaleString()} kg`}
                  />
                </div>
              </div>
              
              <div className="p-4 bg-signal-emerald/10 rounded-xl border border-signal-emerald/20">
                <p className="text-signal-emerald font-semibold text-lg">
                  {activeScenario.pct_of_total_impact}% of total congestion impact eliminated
                </p>
                <p className="text-muted text-sm mt-1">
                  by clearing just {activeScenario.clear_count} junction{activeScenario.clear_count > 1 ? 's' : ''}
                </p>
              </div>
            </div>

            {/* Junctions to Clear */}
            <div>
              <p className="text-xs text-muted uppercase tracking-wider mb-2">Junctions to Clear</p>
              <div className="space-y-2">
                {activeScenario.junctions?.map((junction, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 bg-elevated rounded-lg">
                    <span className="w-6 h-6 rounded-full bg-signal-emerald/20 text-signal-emerald text-xs font-bold flex items-center justify-center">
                      {i + 1}
                    </span>
                    <span className="text-chalk text-sm font-medium truncate flex-1">{junction}</span>
                    <ArrowRight className="w-3 h-3 text-muted" />
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Top Junctions Table */}
      <div className="card">
        <h2 className="font-heading font-semibold text-lg text-chalk mb-4">
          Top 15 High-Impact Junctions
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/[0.06]">
                <th className="text-left py-3 px-4 text-[10px] uppercase tracking-wider text-muted font-medium">#</th>
                <th className="text-left py-3 px-4 text-[10px] uppercase tracking-wider text-muted font-medium">Junction</th>
                <th className="text-right py-3 px-4 text-[10px] uppercase tracking-wider text-muted font-medium">Violations</th>
                <th className="text-right py-3 px-4 text-[10px] uppercase tracking-wider text-muted font-medium">Vehicles/hr</th>
                <th className="text-right py-3 px-4 text-[10px] uppercase tracking-wider text-muted font-medium">Economic Loss</th>
                <th className="text-right py-3 px-4 text-[10px] uppercase tracking-wider text-muted font-medium">Gridlock</th>
              </tr>
            </thead>
            <tbody>
              {topJunctions.map((j, i) => (
                <tr key={i} className="border-b border-white/[0.03] hover:bg-elevated/50 transition-colors">
                  <td className="py-3 px-4 font-mono text-muted text-xs">{i + 1}</td>
                  <td className="py-3 px-4 font-mono text-chalk text-xs">{j.mapped_junction}</td>
                  <td className="py-3 px-4 text-right text-muted text-xs">{j.violation_count}</td>
                  <td className="py-3 px-4 text-right font-mono text-signal-red text-xs">
                    {j.vehicles_blocked?.toLocaleString()}
                  </td>
                  <td className="py-3 px-4 text-right font-mono text-signal-orange text-xs">
                    INR {j.economic_loss?.toLocaleString()}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <span className={`font-mono text-xs font-semibold ${
                      j.avg_gridlock > 70 ? 'text-signal-red' :
                      j.avg_gridlock > 40 ? 'text-signal-orange' : 'text-signal-emerald'
                    }`}>
                      {j.avg_gridlock?.toFixed(1)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function MetricCard({ icon, label, value, color }) {
  return (
    <div className="text-center">
      <div className={`flex justify-center mb-1 ${color}`}>{icon}</div>
      <p className="font-mono font-bold text-xl text-chalk">{value}</p>
      <p className="text-[10px] text-muted uppercase tracking-wider">{label}</p>
    </div>
  )
}

function ImpactRow({ label, value, pct }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted text-sm">{label}</span>
      <span className="font-mono text-chalk font-semibold">{value}</span>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-48 bg-elevated rounded-lg animate-pulse" />
      <div className="card h-32 bg-elevated animate-pulse" />
      <div className="card h-64 bg-elevated animate-pulse" />
    </div>
  )
}
