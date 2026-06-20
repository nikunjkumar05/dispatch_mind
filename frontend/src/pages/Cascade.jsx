import { useApi } from '../utils/api'
import { Route as RouteIcon, ArrowRight, GitBranch, TrendingUp } from 'lucide-react'

export default function Cascade() {
  const { data, loading } = useApi('/cascade')

  if (loading) return <LoadingSkeleton />

  const pairs = data?.pairs || []
  const chains = data?.chains || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-heading font-bold text-2xl text-chalk flex items-center gap-2">
          <RouteIcon className="w-6 h-6 text-khaki" />
          Cascade Proof
        </h1>
        <p className="text-mist/50 text-sm mt-1">
          The domino effect — when one junction jams, nearby junctions follow within 15 minutes
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="card">
          <p className="metric-label">Pairs Tested</p>
          <p className="metric-value">{data?.total_tested?.toLocaleString() || 0}</p>
        </div>
        <div className="card">
          <p className="metric-label">Significant (r&gt;0.2)</p>
          <p className="metric-value text-signal-emerald">{data?.significant_count || 0}</p>
        </div>
        <div className="card">
          <p className="metric-label">Cascade Chains</p>
          <p className="metric-value text-khaki">{chains.length}</p>
        </div>
      </div>

      {/* Cascade Chains */}
      {chains.length > 0 && (
        <div className="card">
          <h2 className="font-heading font-bold text-lg text-chalk mb-4 flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-khaki" />
            Top Cascade Chains
          </h2>
          
          <div className="space-y-4">
            {chains.map((chain, i) => (
              <div key={i} className="p-4 bg-stone/30 rounded-lg border border-mist/10">
                <div className="flex items-center gap-2 flex-wrap">
                  {chain.chain.map((junction, j) => (
                    <span key={j} className="flex items-center gap-2">
                      <span className="px-3 py-1 bg-khaki/20 text-khaki rounded-lg font-mono text-sm font-semibold">
                        {junction}
                      </span>
                      {j < chain.chain.length - 1 && (
                        <ArrowRight className="w-4 h-4 text-mist/30" />
                      )}
                    </span>
                  ))}
                </div>
                <div className="flex gap-6 mt-3 text-sm text-mist/60">
                  <span>
                    Correlation: <span className="font-mono text-chalk">{chain.total_correlation}</span>
                  </span>
                  <span>
                    Distance: <span className="font-mono text-chalk">{chain.total_distance}m</span>
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top Pairs Table */}
      <div className="card">
        <h2 className="font-heading font-bold text-lg text-chalk mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-signal-emerald" />
          Significant Junction Pairs
        </h2>

        {pairs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-mist/10">
                  <th className="text-left py-3 px-4 text-xs uppercase tracking-wider text-mist/50 font-semibold">From</th>
                  <th className="text-left py-3 px-4 text-xs uppercase tracking-wider text-mist/50 font-semibold">To</th>
                  <th className="text-right py-3 px-4 text-xs uppercase tracking-wider text-mist/50 font-semibold">Distance</th>
                  <th className="text-right py-3 px-4 text-xs uppercase tracking-wider text-mist/50 font-semibold">Correlation</th>
                  <th className="text-right py-3 px-4 text-xs uppercase tracking-wider text-mist/50 font-semibold">Violations</th>
                </tr>
              </thead>
              <tbody>
                {pairs.map((pair, i) => (
                  <tr key={i} className="border-b border-mist/5 hover:bg-stone/30 transition-colors">
                    <td className="py-3 px-4 font-mono text-chalk">{pair.from_junction}</td>
                    <td className="py-3 px-4">
                      <span className="flex items-center gap-2">
                        <ArrowRight className="w-4 h-4 text-mist/30" />
                        <span className="font-mono text-chalk">{pair.to_junction}</span>
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-mist/70">{pair.distance_m}m</td>
                    <td className="py-3 px-4 text-right">
                      <span className={`font-mono font-semibold ${
                        pair.correlation > 0.5 ? 'text-signal-emerald' : 
                        pair.correlation > 0.3 ? 'text-khaki' : 'text-mist/70'
                      }`}>
                        {pair.correlation}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right text-mist/70">
                      {pair.violations_from} → {pair.violations_to}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-mist/50 text-center py-8">No significant pairs found</p>
        )}
      </div>

      {/* Explanation */}
      <div className="card border-khaki/20 bg-khaki/5">
        <h3 className="font-heading font-bold text-khaki mb-2">What This Means</h3>
        <p className="text-sm text-mist/70">
          When violations spike at BTP044, nearby junctions like BTP052 see increased violations 
          within 15-30 minutes. This <span className="text-chalk font-semibold">predictive relationship</span> allows 
          BTP to <span className="text-chalk font-semibold">pre-position enforcement</span> before a junction cascades 
          into gridlock. The correlation coefficient (r) measures how strongly one junction predicts another.
        </p>
      </div>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-8 w-48 bg-stone rounded" />
      <div className="grid grid-cols-3 gap-4">
        {[1,2,3].map(i => <div key={i} className="card h-20 bg-stone/30" />)}
      </div>
      <div className="card h-64 bg-stone/30" />
    </div>
  )
}
