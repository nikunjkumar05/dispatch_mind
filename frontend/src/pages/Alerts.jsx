import { useMemo } from 'react'
import { useApi } from '../utils/api'
import { AlertTriangle, Bell, MapPin, Car, Zap } from 'lucide-react'
import ErrorState from '../components/ErrorState'

const priorityConfig = {
  CRITICAL: { color: 'text-signal-red', bg: 'bg-signal-red/10', border: 'border-signal-red/20' },
  HIGH: { color: 'text-tier-high', bg: 'bg-tier-high/10', border: 'border-tier-high/20' },
  MEDIUM: { color: 'text-tier-medium', bg: 'bg-tier-medium/10', border: 'border-tier-medium/20' },
  INFO: { color: 'text-muted', bg: 'bg-elevated', border: 'border-white/[0.06]' },
}

export default function Alerts() {
  const { data, loading, error, refetch } = useApi('/alerts?count=15')

  if (loading) return <PageSkeleton />
  if (error) return <ErrorState message={error} onRetry={refetch} />

  const alerts = data?.alerts || []
  
  const counts = useMemo(() => {
    const c = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, INFO: 0 }
    alerts.forEach(a => { if (c[a.priority] !== undefined) c[a.priority]++ })
    return c
  }, [alerts])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-heading font-bold text-2xl text-chalk flex items-center gap-2">
          <Bell className="w-6 h-6 text-signal-amber" />
          Alert Queue
        </h1>
        <p className="text-muted text-sm mt-1">
          Real-time enforcement alerts — WhatsApp/SMS ready
        </p>
      </div>

      {/* Priority Summary */}
      <div className="grid grid-cols-4 gap-3">
        {['CRITICAL', 'HIGH', 'MEDIUM', 'INFO'].map(p => {
          const config = priorityConfig[p]
          return (
            <div key={p} className={`card ${config.bg} border ${config.border}`}>
              <p className={`text-[10px] font-bold uppercase tracking-wider ${config.color}`}>{p}</p>
              <p className="metric-value text-xl mt-1">{counts[p]}</p>
            </div>
          )
        })}
      </div>

      {/* Alert Cards */}
      <div className="space-y-3">
        {alerts.map((alert, i) => {
          const config = priorityConfig[alert.priority] || priorityConfig.INFO
          return (
            <div key={i} className={`card border ${config.border}`}>
              <div className="flex items-start gap-4">
                {/* Priority Icon */}
                <div className={`p-2 rounded-lg ${config.bg} shrink-0`}>
                  <AlertTriangle className={`w-4 h-4 ${config.color}`} />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <span className={`text-[10px] font-bold uppercase tracking-wider ${config.color}`}>
                      {alert.priority}
                    </span>
                  </div>

                  <h3 className="font-medium text-chalk text-sm truncate">
                    {alert.location?.junction || 'Unknown Junction'}
                  </h3>

                  <div className="flex flex-wrap gap-4 text-xs mt-2 text-muted">
                    <span className="flex items-center gap-1">
                      <Car className="w-3 h-3" />
                      {alert.vehicle?.type} — {alert.vehicle?.number}
                    </span>
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3 h-3" />
                      {alert.location?.police_station}
                    </span>
                    <span className="flex items-center gap-1">
                      <Zap className="w-3 h-3" />
                      CII: <span className="font-mono text-chalk">{alert.scores?.cii}</span>
                    </span>
                  </div>

                  {alert.scores?.cascade_detected && (
                    <span className="inline-flex items-center gap-1 mt-2 px-2 py-0.5 bg-signal-red/10 text-signal-red text-[10px] font-bold rounded-full uppercase tracking-wider">
                      Cascade Detected
                    </span>
                  )}
                </div>

                {/* Action */}
                <div className="text-right shrink-0">
                  <p className="text-xs font-medium text-chalk">{alert.action?.recommended?.replace(/_/g, ' ')}</p>
                  <p className="text-[10px] text-muted mt-1">{alert.action?.target_response_time}</p>
                </div>
              </div>

              {/* WhatsApp Preview */}
              <div className="mt-3 p-3 bg-elevated rounded-lg overflow-hidden">
                <p className="text-[10px] text-muted mb-1 uppercase tracking-wider">WhatsApp Message Preview</p>
                <pre className="text-xs text-muted font-mono whitespace-pre-wrap overflow-x-auto">{alert.message}</pre>
              </div>
            </div>
          )
        })}

        {alerts.length === 0 && (
          <div className="card text-center py-12">
            <Bell className="w-10 h-10 text-muted mx-auto mb-3" />
            <p className="text-muted">No alerts generated</p>
          </div>
        )}
      </div>
    </div>
  )
}

function PageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-48 bg-elevated rounded-lg animate-pulse" />
      <div className="grid grid-cols-4 gap-3">
        {[1,2,3,4].map(i => <div key={i} className="card h-16 bg-elevated animate-pulse" />)}
      </div>
      {[1,2,3].map(i => <div key={i} className="card h-32 bg-elevated animate-pulse" />)}
    </div>
  )
}
