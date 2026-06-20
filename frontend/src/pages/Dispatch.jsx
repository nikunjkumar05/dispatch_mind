import { useState } from 'react'
import { useApi } from '../utils/api'
import { Shield, Truck, MapPin, AlertTriangle, CheckCircle, ExternalLink } from 'lucide-react'
import ErrorState from '../components/ErrorState'
import StatCard from '../components/StatCard'

export default function Dispatch() {
  const [numTrucks, setNumTrucks] = useState(2)
  const { data, loading, error, refetch } = useApi(`/dispatch?num_trucks=${numTrucks}`, [numTrucks])

  if (loading) return <PageSkeleton />
  if (error) return <ErrorState message={error} onRetry={refetch} />

  const routes = data?.routes || []
  const responses = data?.responses || []
  const summary = data?.summary || {}

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-heading font-bold text-2xl text-chalk flex items-center gap-2">
            <Shield className="w-6 h-6 text-accent" />
            Dispatch Plan
          </h1>
          <p className="text-muted text-sm mt-1">
            VRP-optimized tow truck routes for maximum congestion clearance
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="text-sm text-muted">Tow Trucks:</label>
          <select
            value={numTrucks}
            onChange={(e) => setNumTrucks(Number(e.target.value))}
            className="bg-elevated border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-chalk focus:outline-none focus:border-accent/50 transition-colors"
          >
            {[1,2,3,4].map(n => (
              <option key={n} value={n}>{n} truck{n > 1 ? 's' : ''}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Method" value={summary.routing_method || 'N/A'} />
        <StatCard label="Total Stops" value={summary.total_stops || 0} />
        <StatCard label="Distance" value={`${summary.total_distance_km || 0} km`} />
        <StatCard label="Top Hotspot" value={summary.top_hotspot || 'N/A'} icon={AlertTriangle} />
      </div>

      {/* Response Queue */}
      <div className="card">
        <h2 className="font-heading font-semibold text-lg text-chalk mb-4 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-signal-amber" />
          Tiered Response Queue
        </h2>

        <div className="space-y-2">
          {responses.map((resp, i) => (
            <div key={i} className="flex items-center gap-4 p-3 bg-elevated rounded-xl">
              <div className={`p-2 rounded-lg ${
                resp.action === 'PRE_POSITION_TOW_TRUCK' ? 'bg-signal-red/10 text-signal-red' :
                resp.action === 'COMMUNITY_MARSHAL' ? 'bg-signal-amber/10 text-signal-amber' :
                'bg-signal-emerald/10 text-signal-emerald'
              }`}>
                {resp.action === 'PRE_POSITION_TOW_TRUCK' ? <Truck className="w-4 h-4" /> :
                 resp.action === 'COMMUNITY_MARSHAL' ? <MapPin className="w-4 h-4" /> :
                 <CheckCircle className="w-4 h-4" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-chalk text-sm truncate">{resp.junction}</p>
                <p className="text-xs text-muted">{resp.reason}</p>
              </div>
              <span className="text-[10px] font-mono px-2 py-1 rounded-full bg-surface text-muted whitespace-nowrap uppercase tracking-wider">
                {resp.action.replace(/_/g, ' ')}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Truck Routes */}
      {routes.length > 0 && (
        <div className="card">
          <h2 className="font-heading font-semibold text-lg text-chalk mb-4 flex items-center gap-2">
            <Truck className="w-5 h-5 text-accent" />
            Truck Routes
          </h2>

          <div className="space-y-4">
            {routes.map((route, i) => (
              <div key={i} className="p-4 bg-elevated rounded-xl border border-white/[0.06]">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-8 h-8 bg-accent rounded-lg flex items-center justify-center font-mono font-bold text-white text-sm">
                    T{route.truck_id}
                  </div>
                  <div>
                    <p className="font-medium text-chalk text-sm">Truck {route.truck_id}</p>
                    <p className="text-xs text-muted">{route.stops.length} stops · {route.total_distance_km} km</p>
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                  {route.stops.map((stop, j) => (
                    <span key={j} className="flex items-center gap-2">
                      <a 
                        href={`https://www.google.com/maps?q=${stop.lat},${stop.lon}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 px-2 py-1 bg-accent/10 text-accent rounded-lg font-mono text-xs hover:bg-accent/20 transition-colors"
                      >
                        Stop {j + 1}
                        <ExternalLink className="w-3 h-3" />
                      </a>
                      {j < route.stops.length - 1 && (
                        <span className="text-muted">→</span>
                      )}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function PageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-48 bg-elevated rounded-lg animate-pulse" />
      <div className="grid grid-cols-4 gap-4">
        {[1,2,3,4].map(i => <div key={i} className="stat-card h-24 bg-elevated animate-pulse" />)}
      </div>
      <div className="card h-48 bg-elevated animate-pulse" />
    </div>
  )
}
