import { NavLink } from 'react-router-dom'
import { useApi, formatNumber, formatDelay } from '../utils/api'
import { 
  AlertTriangle, Clock, MapPin, Building2, 
  TrendingUp, Shield, Zap
} from 'lucide-react'

export default function Overview() {
  const { data, loading, error } = useApi('/overview')

  if (loading) return <LoadingSkeleton />
  if (error) return <ErrorState message={error} />
  if (!data) return null

  const stats = [
    { label: 'Total Violations', value: formatNumber(data.total_violations), icon: AlertTriangle, color: 'text-khaki' },
    { label: 'Total Delay', value: formatDelay(data.total_delay_veh_min), icon: Clock, color: 'text-signal-amber' },
    { label: 'Active Junctions', value: data.total_junctions, icon: MapPin, color: 'text-signal-emerald' },
    { label: 'Police Stations', value: data.total_stations, icon: Building2, color: 'text-khaki' },
  ]

  const tiers = [
    { label: 'CRITICAL', count: data.critical_count, color: 'bg-tier-critical' },
    { label: 'HIGH', count: data.high_count, color: 'bg-tier-high' },
    { label: 'MEDIUM', count: data.medium_count, color: 'bg-tier-medium' },
    { label: 'LOW', count: data.low_count, color: 'bg-tier-low' },
  ]

  const total = data.critical_count + data.high_count + data.medium_count + data.low_count

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-heading font-bold text-3xl text-chalk flex items-center gap-3">
          <Shield className="w-8 h-8 text-khaki" />
          DispatchMind
        </h1>
        <p className="text-mist/60 mt-1">Your constable's co-pilot. Your city's clear path.</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="card">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg bg-stone/50 ${color}`}>
                <Icon className="w-5 h-5" />
              </div>
              <div>
                <p className="metric-label">{label}</p>
                <p className="metric-value">{value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Impact Tier Breakdown */}
      <div className="card">
        <h2 className="font-heading font-bold text-xl text-chalk mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-khaki" />
          Impact Tier Distribution
        </h2>
        
        <div className="space-y-3">
          {tiers.map(({ label, count, color }) => {
            const pct = total > 0 ? (count / total * 100) : 0
            return (
              <div key={label} className="flex items-center gap-4">
                <span className={`tier-badge ${label}`}>{label}</span>
                <div className="flex-1 h-3 bg-stone rounded-full overflow-hidden">
                  <div 
                    className={`h-full ${color} rounded-full transition-all duration-500`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="font-mono text-sm text-mist/70 w-16 text-right">
                  {count.toLocaleString()}
                </span>
                <span className="font-mono text-xs text-mist/40 w-12 text-right">
                  {pct.toFixed(1)}%
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Pareto Insight */}
      <div className="card border-khaki/30 bg-khaki/5">
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-lg bg-khaki/20">
            <TrendingUp className="w-6 h-6 text-khaki" />
          </div>
          <div>
            <h3 className="font-heading font-bold text-lg text-khaki">The 7% Rule</h3>
            <p className="text-mist/70 mt-1">
              Just <span className="font-mono font-bold text-khaki">{data.pareto_pct}%</span> of violations 
              cause <span className="font-mono font-bold text-khaki">{data.pareto_impact_pct}%</span> of 
              total congestion damage. Focus enforcement on these critical hotspots.
            </p>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <NavLink to="/priority" className="card hover:border-khaki/50 group">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-signal-red group-hover:text-khaki transition-colors" />
            <div>
              <p className="font-semibold text-chalk">Priority Queue</p>
              <p className="text-xs text-mist/50">What to clear right now</p>
            </div>
          </div>
        </NavLink>
        <NavLink to="/map" className="card hover:border-khaki/50 group">
          <div className="flex items-center gap-3">
            <MapPin className="w-5 h-5 text-signal-emerald group-hover:text-khaki transition-colors" />
            <div>
              <p className="font-semibold text-chalk">Map View</p>
              <p className="text-xs text-mist/50">Bengaluru violation hotspots</p>
            </div>
          </div>
        </NavLink>
        <NavLink to="/dispatch" className="card hover:border-khaki/50 group">
          <div className="flex items-center gap-3">
            <Shield className="w-5 h-5 text-khaki" />
            <div>
              <p className="font-semibold text-chalk">Dispatch Plan</p>
              <p className="text-xs text-mist/50">Tow truck routing</p>
            </div>
          </div>
        </NavLink>
      </div>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-8 w-48 bg-stone rounded" />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[1,2,3,4].map(i => (
          <div key={i} className="card h-20 bg-stone/30" />
        ))}
      </div>
      <div className="card h-48 bg-stone/30" />
    </div>
  )
}

function ErrorState({ message }) {
  return (
    <div className="card border-signal-red/30 bg-signal-red/5">
      <p className="text-signal-red font-semibold">Error loading data</p>
      <p className="text-mist/50 text-sm mt-1">{message}</p>
    </div>
  )
}
