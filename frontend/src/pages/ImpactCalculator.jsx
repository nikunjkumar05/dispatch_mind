import { useState } from 'react'
import { useApi } from '../utils/api'
import { Target, TrendingDown, Users, Cloud, ArrowRight, Zap } from 'lucide-react'
import ErrorState from '../components/ErrorState'

export default function ImpactCalculator() {
  const [selectedScenario, setSelectedScenario] = useState(5)
  const { data, loading, error, refetch } = useApi('/impact-summary')

  if (loading) return <LoadingSkeleton />
  if (error) return <ErrorState message={error} onRetry={refetch} />

  const total = data?.total || {}
  const scenarios = data?.scenarios || []
  const topJunctions = data?.top_junctions || []
  const activeScenario = scenarios.find(s => s.clear_count === selectedScenario)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-heading font-bold text-2xl text-chalk flex items-center gap-2">
          <Target className="w-6 h-6 text-signal-emerald" />
          Impact Calculator
        </h1>
        <p className="text-muted text-sm mt-1">
          Clear top junctions to reduce congestion — here's the measurable impact
        </p>
      </div>

      {/* Total Impact Banner */}
      <div className="card border-signal-red/20 bg-signal-red/5">
        <p className="text-xs uppercase tracking-wider text-signal-red font-semibold mb-3">
          Current Total Impact (All Violations)
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard
            icon={<Zap className="w-4 h-4" />}
            label="Vehicles Blocked/hr"
            value={total.vehicles_blocked_hr?.toLocaleString() || '0'}
            color="text-signal-red"
          />
          <MetricCard
            icon={<TrendingDown className="w-4 h-4" />}
            label="Economic Loss/hr"
            value={`INR ${total.economic_loss_inr?.toLocaleString() || '0'}`}
            color="text-signal-orange"
          />
          <MetricCard
            icon={<Users className="w-4 h-4" />}
            label="Person-Hours Blocked"
            value={total.person_hours_blocked?.toLocaleString() || '0'}
            color="text-signal-amber"
          />
          <MetricCard
            icon={<Cloud className="w-4 h-4" />}
            label="CO2 Emissions (kg)"
            value={total.co2_kg?.toLocaleString() || '0'}
            color="text-signal-emerald"
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
