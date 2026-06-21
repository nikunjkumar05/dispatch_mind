import { useApi } from '../utils/api'
import { Route as RouteIcon, ArrowRight, GitBranch, TrendingUp } from 'lucide-react'
import ErrorState from '../components/ErrorState'
import StatCard from '../components/StatCard'

export default function Cascade() {
  const { data, loading, error, refetch } = useApi('/cascade')

  if (loading) return <PageSkeleton />
  if (error) return <ErrorState message={error} onRetry={refetch} />

  const pairs = data?.pairs || []
  const chains = data?.chains || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-heading font-bold text-2xl text-chalk flex items-center gap-2">
          <RouteIcon className="w-6 h-6 text-accent" />
          Cascade Proof
        </h1>
        <p className="text-muted text-sm mt-1">
          The domino effect — when one junction jams, nearby junctions follow within 15 minutes
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Pairs Tested" value={data?.total_tested || 0} />
        <StatCard label="Significant (r>0.2)" value={data?.significant_count || 0} icon={TrendingUp} />
        <StatCard label="Cascade Chains" value={chains.length} icon={GitBranch} />
      </div>

      {/* Cascade Chains */}
      {chains.length > 0 && (
        <div className="card">
          <h2 className="font-heading font-semibold text-lg text-chalk mb-4 flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-accent" />
            Top Cascade Chains
          </h2>
          
          <div className="space-y-4">
            {chains.map((chain, i) => (
              <div key={i} className="p-4 bg-elevated rounded-xl border border-white/[0.06]">
                <div className="flex items-center gap-2 flex-wrap">
                  {chain.chain.map((junction, j) => (
                    <span key={j} className="flex items-center gap-2">
                      <span className="px-3 py-1.5 bg-accent/10 text-accent rounded-lg font-mono text-xs font-medium">
                        {junction}
                      </span>
                      {j < chain.chain.length - 1 && (
                        <ArrowRight className="w-4 h-4 text-muted" />
                      )}
                    </span>
                  ))}
                </div>
                <div className="flex gap-6 mt-3 text-sm text-muted">
                  <span>
                    Correlation: <span className="font-mono text-chalk font-medium">{chain.total_correlation}</span>
                  </span>
                  <span>
                    Distance: <span className="font-mono text-chalk font-medium">{chain.total_distance}m</span>
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top Pairs Table */}
      <div className="card">
        <h2 className="font-heading font-semibold text-lg text-chalk mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-signal-emerald" />
          Significant Junction Pairs
        </h2>

        {pairs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  <th className="text-left py-3 px-4 text-[10px] uppercase tracking-wider text-muted font-medium">From</th>
                  <th className="text-left py-3 px-4 text-[10px] uppercase tracking-wider text-muted font-medium">To</th>
                  <th className="text-right py-3 px-4 text-[10px] uppercase tracking-wider text-muted font-medium">Distance</th>
                  <th className="text-right py-3 px-4 text-[10px] uppercase tracking-wider text-muted font-medium">Correlation</th>
                  <th className="text-right py-3 px-4 text-[10px] uppercase tracking-wider text-muted font-medium">Violations</th>
                </tr>
              </thead>
              <tbody>
                {pairs.map((pair, i) => (
                  <tr key={i} className="border-b border-white/[0.03] hover:bg-elevated/50 transition-colors">
                    <td className="py-3 px-4 font-mono text-chalk text-xs">{pair.from_junction}</td>
                    <td className="py-3 px-4">
                      <span className="flex items-center gap-2">
                        <ArrowRight className="w-3 h-3 text-muted" />
                        <span className="font-mono text-chalk text-xs">{pair.to_junction}</span>
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-muted text-xs">{pair.distance_m}m</td>
                    <td className="py-3 px-4 text-right">
                      <span className={`font-mono font-semibold text-xs ${
                        pair.correlation > 0.5 ? 'text-signal-emerald' : 
                        pair.correlation > 0.3 ? 'text-accent' : 'text-muted'
                      }`}>
                        {pair.correlation}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right text-muted text-xs">
                      {pair.violations_from} → {pair.violations_to}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-muted text-center py-8">No significant pairs found</p>
        )}
      </div>

      {/* Explanation */}
      <div className="card border-accent/20 bg-accent/5 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-accent to-transparent" />
        <h3 className="font-heading font-semibold text-accent mb-2">What This Means</h3>
        <p className="text-sm text-muted leading-relaxed">
          When violations spike at one junction, nearby junctions see increased violations 
          within 15-30 minutes. This <span className="text-chalk font-medium">predictive relationship</span> allows 
          BTP to <span className="text-chalk font-medium">pre-position enforcement</span> before a junction cascades 
          into gridlock. The correlation coefficient (r) measures how strongly one junction predicts another.
        </p>
      </div>
    </div>
  )
}

function PageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-48 bg-elevated rounded-lg animate-pulse" />
      <div className="grid grid-cols-3 gap-4">
        {[1,2,3].map(i => <div key={i} className="stat-card h-24 bg-elevated animate-pulse" />)}
      </div>
      <div className="card h-64 bg-elevated animate-pulse" />
    </div>
  )
}
