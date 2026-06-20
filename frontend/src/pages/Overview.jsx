import { NavLink } from 'react-router-dom'
import { useApi, formatDelay } from '../utils/api'
import { 
  AlertTriangle, Clock, MapPin, Building2, 
  TrendingUp, Shield, Zap, ArrowRight
} from 'lucide-react'
import LoadingSkeleton from '../components/LoadingSkeleton'
import ErrorState from '../components/ErrorState'
import StatCard from '../components/StatCard'

export default function Overview() {
  const { data, loading, error, refetch } = useApi('/overview')

  if (loading) return <PageSkeleton />
  if (error) return <ErrorState message={error} onRetry={refetch} />
  if (!data) return null

  const stats = [
    { label: 'Total Violations', value: data.total_violations, icon: AlertTriangle },
    { label: 'Total Delay', value: formatDelay(data.total_delay_veh_min), icon: Clock },
    { label: 'Active Junctions', value: data.total_junctions, icon: MapPin },
    { label: 'Police Stations', value: data.total_stations, icon: Building2 },
  ]

  const tiers = [
    { label: 'CRITICAL', count: data.critical_count, color: 'bg-tier-critical', glow: 'shadow-glow-red' },
    { label: 'HIGH', count: data.high_count, color: 'bg-tier-high', glow: 'shadow-glow-orange' },
    { label: 'MEDIUM', count: data.medium_count, color: 'bg-tier-medium', glow: 'shadow-glow-amber' },
    { label: 'LOW', count: data.low_count, color: 'bg-tier-low', glow: 'shadow-glow-green' },
  ]

  const total = data.critical_count + data.high_count + data.medium_count + data.low_count

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-heading font-bold text-2xl text-chalk flex items-center gap-3">
          <Shield className="w-7 h-7 text-accent" />
          DispatchMind
        </h1>
        <p className="text-muted mt-1">Your constable's co-pilot. Your city's clear path.</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <StatCard key={stat.label} {...stat} />
        ))}
      </div>

      {/* Impact Tier Breakdown */}
      <div className="card">
        <h2 className="font-heading font-semibold text-lg text-chalk mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-accent" />
          Impact Tier Distribution
        </h2>
        
        <div className="space-y-3">
          {tiers.map(({ label, count, color, glow }) => {
            const pct = total > 0 ? (count / total * 100) : 0
            return (
              <div key={label} className="flex items-center gap-4">
                <span className={`tier-badge ${label}`}>{label}</span>
                <div className="flex-1 h-2.5 bg-elevated rounded-full overflow-hidden">
                  <div 
                    className={`h-full ${color} rounded-full transition-all duration-700 ease-out`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="font-mono text-sm text-chalk w-16 text-right font-medium">
                  {count.toLocaleString()}
                </span>
                <span className="font-mono text-xs text-muted w-12 text-right">
                  {pct.toFixed(1)}%
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Pareto Insight */}
      <div className="card border-accent/20 bg-accent/5 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-accent to-transparent" />
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-xl bg-accent/10">
            <TrendingUp className="w-6 h-6 text-accent" />
          </div>
          <div>
            <h3 className="font-heading font-semibold text-base text-accent">The 7% Rule</h3>
            <p className="text-muted mt-1 leading-relaxed">
              Just <span className="font-mono font-bold text-chalk">{data.pareto_pct}%</span> of violations 
              cause <span className="font-mono font-bold text-chalk">{data.pareto_impact_pct}%</span> of 
              total congestion severity. Focus enforcement on these critical hotspots.
            </p>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <NavLink to="/priority" className="card group hover:border-accent/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-signal-red/10">
                <AlertTriangle className="w-5 h-5 text-signal-red" />
              </div>
              <div>
                <p className="font-semibold text-chalk text-sm">Priority Queue</p>
                <p className="text-xs text-muted">What to clear right now</p>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-muted group-hover:text-accent group-hover:translate-x-1 transition-all" />
          </div>
        </NavLink>
        <NavLink to="/map" className="card group hover:border-accent/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-signal-emerald/10">
                <MapPin className="w-5 h-5 text-signal-emerald" />
              </div>
              <div>
                <p className="font-semibold text-chalk text-sm">Map View</p>
                <p className="text-xs text-muted">Bengaluru violation hotspots</p>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-muted group-hover:text-accent group-hover:translate-x-1 transition-all" />
          </div>
        </NavLink>
        <NavLink to="/dispatch" className="card group hover:border-accent/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-accent/10">
                <Shield className="w-5 h-5 text-accent" />
              </div>
              <div>
                <p className="font-semibold text-chalk text-sm">Dispatch Plan</p>
                <p className="text-xs text-muted">Tow truck routing</p>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-muted group-hover:text-accent group-hover:translate-x-1 transition-all" />
          </div>
        </NavLink>
      </div>
    </div>
  )
}

function PageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-48 bg-elevated rounded-lg animate-pulse" />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[1,2,3,4].map(i => (
          <div key={i} className="stat-card h-24 bg-elevated animate-pulse" />
        ))}
      </div>
      <div className="card h-48 bg-elevated animate-pulse" />
    </div>
  )
}
