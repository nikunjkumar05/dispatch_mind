import { useState } from 'react'
import { useApi, formatDelay } from '../utils/api'
import { Sliders, TrendingDown, AlertTriangle, MapPin, Zap } from 'lucide-react'

const SCENARIOS = [1, 5, 10, 15, 20]

export default function Simulator() {
  const [clearCount, setClearCount] = useState(10)
  const [filterStation, setFilterStation] = useState('ALL')
  const [filterTier, setFilterTier] = useState('ALL')

  const { data: stationData } = useApi('/stations')
  const { data, loading } = useApi(
    `/simulator?top_n=${clearCount}&filter_station=${filterStation}&filter_tier=${filterTier}`,
    [clearCount, filterStation, filterTier]
  )

  const stationList = stationData?.stations || []
  const baseline = data?.baseline || {}
  const scenarios = data?.scenarios || []
  const activeScenario = scenarios.find(s => s.clear_count === clearCount)

  if (loading) return <LoadingSkeleton />

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-heading font-bold text-2xl text-chalk flex items-center gap-2">
          <Sliders className="w-6 h-6 text-accent" />
          Enforcement Impact Calculator
        </h1>
        <p className="text-muted text-sm mt-1">
          See the impact of clearing top violations on overall congestion severity
        </p>
      </div>

      {/* Controls */}
      <div className="card">
        <h2 className="font-heading font-semibold text-lg text-chalk mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-accent" />
          Scenario Controls
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Clear Count Slider */}
          <div>
            <label className="text-xs uppercase tracking-wider text-muted font-semibold">
              Clear Top N Violations
            </label>
            <div className="mt-2">
              <input
                type="range"
                min="1"
                max="20"
                value={clearCount}
                onChange={(e) => setClearCount(Number(e.target.value))}
                className="w-full accent-accent"
              />
              <div className="flex justify-between mt-1">
                <span className="text-xs text-muted">1</span>
                <span className="text-sm font-mono font-bold text-chalk">{clearCount}</span>
                <span className="text-xs text-muted">20</span>
              </div>
            </div>
          </div>

          {/* Station Filter */}
          <div>
            <label className="text-xs uppercase tracking-wider text-muted font-semibold">
              Police Station
            </label>
            <select
              value={filterStation}
              onChange={(e) => setFilterStation(e.target.value)}
              className="mt-2 w-full bg-elevated border border-muted/20 rounded-lg px-3 py-2 text-sm text-chalk focus:outline-none focus:border-accent"
            >
              <option value="ALL">All Stations</option>
              {stationList.map(s => (
                <option key={s.station} value={s.station}>{s.station}</option>
              ))}
            </select>
          </div>

          {/* Tier Filter */}
          <div>
            <label className="text-xs uppercase tracking-wider text-muted font-semibold">
              Impact Tier
            </label>
            <select
              value={filterTier}
              onChange={(e) => setFilterTier(e.target.value)}
              className="mt-2 w-full bg-elevated border border-muted/20 rounded-lg px-3 py-2 text-sm text-chalk focus:outline-none focus:border-accent"
            >
              <option value="ALL">All Tiers</option>
              <option value="CRITICAL">CRITICAL</option>
              <option value="HIGH">HIGH</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="LOW">LOW</option>
            </select>
          </div>
        </div>
      </div>

      {/* Baseline vs Cleared */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card border-muted/20">
          <p className="text-xs uppercase tracking-wider text-muted font-semibold mb-1">Current Baseline</p>
          <p className="metric-value">{baseline.cost?.toLocaleString()}</p>
          <p className="text-xs text-muted mt-1">total congestion severity score</p>
          <div className="flex gap-4 mt-3 text-sm text-muted">
            <span>{baseline.violations?.toLocaleString()} violations</span>
            <span>{baseline.junctions} junctions</span>
          </div>
        </div>

        {activeScenario && (
          <div className="card border-signal-emerald/30 bg-signal-emerald/5">
            <p className="text-xs uppercase tracking-wider text-signal-emerald font-semibold mb-1">
              After Clearing {activeScenario.clear_count}
            </p>
            <div className="flex items-baseline gap-3">
              <p className="metric-value text-signal-emerald">{activeScenario.remaining_cost?.toLocaleString()}</p>
              <span className="text-sm font-mono text-signal-emerald font-bold">
                -{activeScenario.pct_reduction}%
              </span>
            </div>
            <p className="text-xs text-muted mt-1">remaining congestion severity</p>
            <div className="flex gap-4 mt-3 text-sm text-muted">
              <span>{activeScenario.violations_cleared} cleared</span>
              <span>Top: {activeScenario.top_junction}</span>
            </div>
          </div>
        )}
      </div>

      {/* Scenario Comparison */}
      {scenarios.length > 0 && (
        <div className="card">
          <h2 className="font-heading font-semibold text-lg text-chalk mb-4 flex items-center gap-2">
            <TrendingDown className="w-5 h-5 text-signal-emerald" />
            Scenario Comparison
          </h2>

          <div className="space-y-3">
            {scenarios.map((scenario) => (
              <button
                key={scenario.clear_count}
                onClick={() => setClearCount(scenario.clear_count)}
                className={`w-full text-left p-4 rounded-lg border transition-all ${
                  clearCount === scenario.clear_count
                    ? 'border-accent bg-accent/10'
                    : 'border-muted/10 bg-elevated/50 hover:border-muted/30'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center font-heading font-bold text-sm ${
                      clearCount === scenario.clear_count
                        ? 'bg-accent text-chalk'
                        : 'bg-muted/20 text-muted'
                    }`}>
                      {scenario.clear_count}
                    </div>
                    <div>
                      <p className="font-semibold text-chalk text-sm">
                        Clear top {scenario.clear_count} violations
                      </p>
                      <p className="text-xs text-muted">
                        {scenario.tier_impact?.CRITICAL || 0} critical, {scenario.tier_impact?.HIGH || 0} high
                      </p>
                    </div>
                  </div>

                  <div className="text-right">
                    <p className="font-mono font-bold text-signal-emerald">
                      -{scenario.pct_reduction}%
                    </p>
                    <p className="text-xs text-muted">
                      -{scenario.cleared_cost?.toLocaleString()} score
                    </p>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="mt-3 h-2 bg-muted/10 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-signal-emerald rounded-full transition-all duration-500"
                    style={{ width: `${scenario.pct_reduction}%` }}
                  />
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Insight */}
      {activeScenario && (
        <div className="card border-accent/20 bg-accent/5">
          <h3 className="font-heading font-semibold text-accent mb-2">Operational Insight</h3>
          <p className="text-sm text-muted leading-relaxed">
            Clearing just <span className="text-chalk font-bold">{activeScenario.clear_count}</span> 
            {activeScenario.clear_count === 1 ? ' violation' : ' violations'} 
            ({activeScenario.pct_reduction}% of total severity) would disproportionately 
            impact <span className="text-chalk font-semibold">{activeScenario.top_junction}</span>. 
            This demonstrates the <span className="text-chalk font-semibold">Pareto principle</span> — 
            a small number of high-impact violations cause most of the congestion damage.
          </p>
        </div>
      )}
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-8 w-48 bg-elevated rounded-lg" />
      <div className="card h-40 bg-elevated" />
      <div className="grid grid-cols-2 gap-4">
        <div className="card h-32 bg-elevated" />
        <div className="card h-32 bg-elevated" />
      </div>
      <div className="card h-64 bg-elevated" />
    </div>
  )
}
