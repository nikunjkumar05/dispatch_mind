import { useState, useEffect } from 'react';
import { ChartBar as BarChart3, Users, MapPin, TrendingUp, TriangleAlert as AlertTriangle, Activity, Clock, CircleCheck as CheckCircle, Target, ChevronRight, RefreshCw, Radio, Car, Building2, TrendingDown, Zap, Volume2, FileText } from 'lucide-react';

export default function ACPDashboard() {
  const [overview, setOverview] = useState(null)
  const [capacity, setCapacity] = useState(null)
  const [tipping, setTipping] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch('/api/overview').then(r => r.json()).catch(() => null),
      fetch('/api/capacity-status').then(r => r.json()).catch(() => null),
      fetch('/api/tipping-points').then(r => r.json()).catch(() => null),
    ]).then(([o, c, t]) => {
      setOverview(o)
      setCapacity(c)
      setTipping(t)
      setLoading(false)
    })
  }, [])

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <div className="h-32 bg-elevated rounded-xl animate-pulse" />
        <div className="grid grid-cols-4 gap-4">
          {[1,2,3,4].map(i => <div key={i} className="h-24 bg-elevated rounded-xl animate-pulse" />)}
        </div>
      </div>
    )
  }

  // Capacity status summary
  const junctions = capacity?.junctions || []
  const redCount = junctions.filter(j => j.status === 'RED').length
  const yellowCount = junctions.filter(j => j.status === 'YELLOW').length
  const greenCount = junctions.filter(j => j.status === 'GREEN').length

  const criticalTipping = tipping?.predictions?.filter(p => p.status === 'CRITICAL') || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-chalk flex items-center gap-2">
            <Building2 className="w-6 h-6 text-accent" />
            ACP Command Center
          </h1>
          <p className="text-muted text-sm mt-1">
            City-wide parking enforcement intelligence
          </p>
        </div>
        <button
          onClick={() => window.location.reload()}
          className="flex items-center gap-2 px-3 py-1.5 bg-elevated border border-white/[0.08] rounded-lg text-sm text-muted hover:text-chalk transition-all"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      {/* Hero Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-signal-red/10 border border-signal-red/20">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-3 h-3 rounded-full bg-signal-red" />
            <span className="text-xs text-signal-red font-bold uppercase tracking-wider">Critical</span>
          </div>
          <p className="text-3xl font-bold text-signal-red">{redCount}</p>
          <p className="text-xs text-muted mt-1">Junctions below 50% capacity</p>
        </div>

        <div className="p-4 rounded-xl bg-signal-amber/10 border border-signal-amber/20">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-3 h-3 rounded-full bg-signal-amber" />
            <span className="text-xs text-signal-amber font-bold uppercase tracking-wider">Warning</span>
          </div>
          <p className="text-3xl font-bold text-signal-amber">{yellowCount}</p>
          <p className="text-xs text-muted mt-1">Junctions 50-70% capacity</p>
        </div>

        <div className="p-4 rounded-xl bg-signal-emerald/10 border border-signal-emerald/20">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-3 h-3 rounded-full bg-signal-emerald" />
            <span className="text-xs text-signal-emerald font-bold uppercase tracking-wider">Normal</span>
          </div>
          <p className="text-3xl font-bold text-signal-emerald">{greenCount}</p>
          <p className="text-xs text-muted mt-1">Junctions above 70% capacity</p>
        </div>

        <div className="p-4 rounded-xl bg-elevated border border-white/[0.06]">
          <div className="flex items-center gap-2 mb-2">
            <Volume2 className="w-4 h-4 text-accent" />
            <span className="text-xs text-muted font-bold uppercase tracking-wider">Voice Alerts</span>
          </div>
          <p className="text-3xl font-bold text-chalk">{criticalTipping.length}</p>
          <p className="text-xs text-muted mt-1">Predictions need dispatch</p>
        </div>
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Tipping Points + Anomalies */}
        <div className="lg:col-span-2 space-y-4">
          {/* Tipping Point Predictions */}
          <div className="card border border-white/[0.06]">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-bold text-chalk flex items-center gap-2">
                  <Zap className="w-5 h-5 text-signal-amber" />
                  Tipping Point Predictions
                </h2>
                <p className="text-xs text-muted mt-0.5">
                  Predictive vs Reactive — AI-detected congestion spikes
                </p>
              </div>
              <span className="px-2 py-0.5 bg-signal-red/10 text-signal-red text-[10px] font-bold rounded uppercase">
                {tipping?.total_junctions_with_tipping_points || 0} Detected
              </span>
            </div>

            {criticalTipping.length === 0 ? (
              <div className="text-center py-8">
                <Activity className="w-8 h-8 text-signal-emerald mx-auto mb-2" />
                <p className="text-muted">No critical tipping points</p>
              </div>
            ) : (
              <div className="space-y-2">
                {criticalTipping.slice(0, 5).map((pred, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-elevated/50 border border-white/[0.04] hover:border-signal-red/20 transition-colors">
                    <div className="flex items-center gap-3">
                      <Clock className="w-4 h-4 text-signal-red" />
                      <div>
                        <p className="text-sm font-medium text-chalk">{pred.junction}</p>
                        <p className="text-xs text-muted">{pred.message}</p>
                      </div>
                    </div>
                    <span className="px-2 py-0.5 bg-signal-amber/10 text-signal-amber text-[10px] font-bold rounded">
                      {pred.predicted_time}
                    </span>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-4 p-3 bg-black/20 rounded-lg text-xs text-muted flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5" />
              {tipping?.methodology || '7-hour rolling window, 3-sigma detection'}
            </div>
          </div>

          {/* Capacity Loss by Junction */}
          <div className="card border border-white/[0.06]">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-chalk">
                Road Capacity Loss
              </h2>
              <span className="text-xs text-muted">
                Core ClearLane Innovation
              </span>
            </div>

            <div className="space-y-2 max-h-64 overflow-y-auto">
              {junctions.slice(0, 8).map((j, idx) => (
                <div key={idx} className="flex items-center gap-4 p-3 rounded-lg bg-elevated/30">
                  <div className={`w-3 h-3 rounded-full ${
                    j.status === 'RED' ? 'bg-signal-red' :
                    j.status === 'YELLOW' ? 'bg-signal-amber' : 'bg-signal-emerald'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-chalk truncate">{j.junction}</p>
                    <p className="text-xs text-muted">{j.violation_count} violations</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-chalk">
                      {j.capacity_loss_pct?.toFixed(1) || 0}%
                    </p>
                    <p className="text-xs text-muted">lost</p>
                  </div>
                  <div className="w-24">
                    <div className="h-2 bg-elevated rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          j.status === 'RED' ? 'bg-signal-red' :
                          j.status === 'YELLOW' ? 'bg-signal-amber' : 'bg-signal-emerald'
                        }`}
                        style={{ width: `${j.capacity_loss_pct || 0}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Quick Stats + Actions */}
        <div className="space-y-4">
          {/* City Summary */}
          <div className="card border border-white/[0.06]">
            <h3 className="text-sm font-bold text-chalk mb-4">City-Wide Impact</h3>
            <div className="space-y-3">
              <div className="p-3 rounded-lg bg-elevated/30">
                <p className="text-xs text-muted">Vehicles Blocked/Hour</p>
                <p className="text-xl font-bold text-chalk">
                  {overview?.vehicles_blocked_hr?.toLocaleString() || 0}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-elevated/30">
                <p className="text-xs text-muted">Economic Loss</p>
                <p className="text-xl font-bold text-signal-red">
                  {(overview?.economic_loss_inr || 0).toLocaleString('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-elevated/30">
                <p className="text-xs text-muted">CO2 Emissions</p>
                <p className="text-xl font-bold text-chalk">
                  {(overview?.co2_kg || 0).toLocaleString()} kg
                </p>
              </div>
            </div>
          </div>

          {/* Violation Tiers */}
          <div className="card border border-white/[0.06]">
            <h3 className="text-sm font-bold text-chalk mb-4">Impact Tiers</h3>
            <div className="space-y-2">
              {[
                { label: 'CRITICAL', count: overview?.critical_count || 0, color: 'signal-red' },
                { label: 'HIGH', count: overview?.high_count || 0, color: 'tier-high' },
                { label: 'MEDIUM', count: overview?.medium_count || 0, color: 'tier-medium' },
                { label: 'LOW', count: overview?.low_count || 0, color: 'tier-low' },
              ].map((tier) => (
                <div key={tier.label} className="flex items-center justify-between p-2 rounded bg-elevated/30">
                  <span className={`text-xs font-bold text-${tier.color}`}>{tier.label}</span>
                  <span className="text-sm text-chalk">{tier.count.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="card border border-white/[0.06]">
            <h3 className="text-sm font-bold text-chalk mb-4">Quick Actions</h3>
            <div className="space-y-2">
              <button className="w-full flex items-center gap-2 px-3 py-2 bg-accent/10 border border-accent/20 rounded-lg text-accent text-sm hover:bg-accent/20 transition-colors">
                <Radio className="w-4 h-4" />
                Open Command Center
              </button>
              <button className="w-full flex items-center gap-2 px-3 py-2 bg-elevated border border-white/[0.06] rounded-lg text-muted text-sm hover:text-chalk transition-colors">
                <FileText className="w-4 h-4" />
                Generate Enforcement Report
              </button>
              <button className="w-full flex items-center gap-2 px-3 py-2 bg-elevated border border-white/[0.06] rounded-lg text-muted text-sm hover:text-chalk transition-colors">
                <MapPin className="w-4 h-4" />
                View Map
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
