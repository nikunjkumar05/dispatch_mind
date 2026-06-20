import { useApi, tierColor } from '../utils/api'
import { AlertTriangle, Bell, Clock, MapPin, Car, Zap } from 'lucide-react'

export default function Alerts() {
  const { data, loading } = useApi('/alerts?count=15')

  if (loading) return <LoadingSkeleton />

  const alerts = data?.alerts || []

  const priorityConfig = {
    CRITICAL: { color: 'text-signal-red', bg: 'bg-signal-red/10', border: 'border-signal-red/30' },
    HIGH: { color: 'text-tier-high', bg: 'bg-tier-high/10', border: 'border-tier-high/30' },
    MEDIUM: { color: 'text-tier-medium', bg: 'bg-tier-medium/10', border: 'border-tier-medium/30' },
    INFO: { color: 'text-mist/50', bg: 'bg-stone/30', border: 'border-mist/10' },
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-heading font-bold text-2xl text-chalk flex items-center gap-2">
          <Bell className="w-6 h-6 text-signal-amber" />
          Alert Queue
        </h1>
        <p className="text-mist/50 text-sm mt-1">
          Real-time enforcement alerts — WhatsApp/SMS ready
        </p>
      </div>

      {/* Priority Summary */}
      <div className="grid grid-cols-4 gap-3">
        {['CRITICAL', 'HIGH', 'MEDIUM', 'INFO'].map(p => {
          const count = alerts.filter(a => a.priority === p).length
          const config = priorityConfig[p]
          return (
            <div key={p} className={`card ${config.bg} border ${config.border}`}>
              <p className={`text-xs font-bold uppercase tracking-wider ${config.color}`}>{p}</p>
              <p className="metric-value text-xl">{count}</p>
            </div>
          )
        })}
      </div>

      {/* Alert Cards */}
      <div className="space-y-4">
        {alerts.map((alert, i) => {
          const config = priorityConfig[alert.priority] || priorityConfig.INFO
          return (
            <div key={i} className={`card border ${config.border}`}>
              <div className="flex items-start gap-4">
                {/* Priority Icon */}
                <div className={`p-2 rounded-lg ${config.bg}`}>
                  <AlertTriangle className={`w-5 h-5 ${config.color}`} />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <span className={`text-xs font-bold uppercase tracking-wider ${config.color}`}>
                      {alert.priority}
                    </span>
                    <span className="text-xs text-mist/30">{alert.alert_id}</span>
                  </div>

                  <h3 className="font-semibold text-chalk truncate">
                    {alert.location?.junction || 'Unknown Junction'}
                  </h3>

                  <div className="flex flex-wrap gap-4 text-sm mt-2 text-mist/60">
                    <span className="flex items-center gap-1">
                      <Car className="w-4 h-4" />
                      {alert.vehicle?.type} — {alert.vehicle?.number}
                    </span>
                    <span className="flex items-center gap-1">
                      <MapPin className="w-4 h-4" />
                      {alert.location?.police_station}
                    </span>
                    <span className="flex items-center gap-1">
                      <Zap className="w-4 h-4" />
                      CII: <span className="font-mono text-chalk">{alert.scores?.cii}</span>
                    </span>
                  </div>

                  {alert.scores?.cascade_detected && (
                    <span className="inline-flex items-center gap-1 mt-2 px-2 py-0.5 bg-signal-red/20 text-signal-red text-xs font-semibold rounded">
                      CASCADE DETECTED
                    </span>
                  )}
                </div>

                {/* Action */}
                <div className="text-right">
                  <p className="text-xs font-semibold text-chalk">{alert.action?.recommended?.replace(/_/g, ' ')}</p>
                  <p className="text-xs text-mist/40 mt-1">{alert.action?.target_response_time}</p>
                </div>
              </div>

              {/* WhatsApp Preview */}
              <div className="mt-3 p-3 bg-stone/30 rounded-lg">
                <p className="text-xs text-mist/40 mb-1">WhatsApp Message Preview:</p>
                <pre className="text-xs text-mist/70 font-mono whitespace-pre-wrap">{alert.message}</pre>
              </div>
            </div>
          )
        })}

        {alerts.length === 0 && (
          <div className="card text-center py-8">
            <p className="text-mist/50">No alerts generated</p>
          </div>
        )}
      </div>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-8 w-48 bg-stone rounded" />
      <div className="grid grid-cols-4 gap-3">
        {[1,2,3,4].map(i => <div key={i} className="card h-16 bg-stone/30" />)}
      </div>
      {[1,2,3].map(i => <div key={i} className="card h-32 bg-stone/30" />)}
    </div>
  )
}
