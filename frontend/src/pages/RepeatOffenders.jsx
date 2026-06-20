import { useMemo } from 'react'
import { useApi, formatDelay } from '../utils/api'
import { Users, AlertTriangle, MapPin } from 'lucide-react'
import ErrorState from '../components/ErrorState'
import StatCard from '../components/StatCard'

export default function RepeatOffenders() {
  const { data, loading, error, refetch } = useApi('/repeat-offenders?min_violations=3')

  if (loading) return <PageSkeleton />
  if (error) return <ErrorState message={error} onRetry={refetch} />

  const offenders = data?.offenders || []
  
  const totalHighImpact = useMemo(() => 
    offenders.reduce((sum, o) => sum + o.violation_count, 0), [offenders])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-heading font-bold text-2xl text-chalk flex items-center gap-2">
          <Users className="w-6 h-6 text-tier-high" />
          Repeat Offenders
        </h1>
        <p className="text-muted text-sm mt-1">
          The &lt;1% of vehicles responsible for &gt;20% of high-impact violations
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4">
        <StatCard label="Repeat Offenders" value={data?.total_count || 0} />
        <StatCard label="Total High-Impact" value={totalHighImpact} icon={AlertTriangle} />
      </div>

      {/* Offenders Table */}
      <div className="card">
        <h2 className="font-heading font-semibold text-lg text-chalk mb-4 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-signal-red" />
          Top Serial Blockers
        </h2>

        {offenders.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  <th className="text-left py-3 px-4 text-[10px] uppercase tracking-wider text-muted font-medium">Vehicle</th>
                  <th className="text-left py-3 px-4 text-[10px] uppercase tracking-wider text-muted font-medium">Type</th>
                  <th className="text-right py-3 px-4 text-[10px] uppercase tracking-wider text-muted font-medium">Violations</th>
                  <th className="text-right py-3 px-4 text-[10px] uppercase tracking-wider text-muted font-medium">Total Delay</th>
                  <th className="text-left py-3 px-4 text-[10px] uppercase tracking-wider text-muted font-medium">Stations</th>
                  <th className="text-left py-3 px-4 text-[10px] uppercase tracking-wider text-muted font-medium">Types</th>
                </tr>
              </thead>
              <tbody>
                {offenders.map((offender, i) => (
                  <tr key={i} className="border-b border-white/[0.03] hover:bg-elevated/50 transition-colors">
                    <td className="py-3 px-4">
                      <span className="font-mono font-medium text-chalk text-xs">{offender.vehicle_number}</span>
                    </td>
                    <td className="py-3 px-4 text-muted text-xs">{offender.top_vehicle}</td>
                    <td className="py-3 px-4 text-right">
                      <span className="font-mono font-bold text-signal-red">{offender.violation_count}</span>
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-muted text-xs">
                      {formatDelay(offender.total_delay)}
                    </td>
                    <td className="py-3 px-4 text-muted text-xs max-w-[200px] truncate" title={offender.stations}>
                      {offender.stations}
                    </td>
                    <td className="py-3 px-4 text-muted text-xs max-w-[200px] truncate" title={offender.violation_types}>
                      {offender.violation_types}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12">
            <Users className="w-10 h-10 text-muted mx-auto mb-3" />
            <p className="text-muted">No repeat offenders found</p>
          </div>
        )}
      </div>

      {/* Insight */}
      <div className="card border-tier-high/20 bg-tier-high/5 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-tier-high to-transparent" />
        <h3 className="font-heading font-semibold text-tier-high mb-2">Operational Insight</h3>
        <p className="text-sm text-muted leading-relaxed">
          These vehicles operate across multiple police jurisdictions, exploiting gaps in enforcement.
          A <span className="text-chalk font-medium">centralized alert system</span> that flags these 
          plate numbers at entry points would significantly reduce repeat violations.
        </p>
      </div>
    </div>
  )
}

function PageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-48 bg-elevated rounded-lg animate-pulse" />
      <div className="grid grid-cols-2 gap-4">
        {[1,2].map(i => <div key={i} className="stat-card h-24 bg-elevated animate-pulse" />)}
      </div>
      <div className="card h-64 bg-elevated animate-pulse" />
    </div>
  )
}
