import { useState } from 'react'
import { useApi, tierColor } from '../utils/api'
import { Shield, Truck, MapPin, Clock, AlertTriangle, CheckCircle } from 'lucide-react'

export default function Dispatch() {
  const [numTrucks, setNumTrucks] = useState(2)
  const { data, loading } = useApi(`/dispatch?num_trucks=${numTrucks}`, [numTrucks])

  if (loading) return <LoadingSkeleton />

  const routes = data?.routes || []
  const responses = data?.responses || []
  const summary = data?.summary || {}

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-heading font-bold text-2xl text-chalk flex items-center gap-2">
            <Shield className="w-6 h-6 text-khaki" />
            Dispatch Plan
          </h1>
          <p className="text-mist/50 text-sm mt-1">
            VRP-optimized tow truck routes for maximum congestion clearance
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="text-sm text-mist/60">Tow Trucks:</label>
          <select
            value={numTrucks}
            onChange={(e) => setNumTrucks(Number(e.target.value))}
            className="bg-stone/50 border border-mist/20 rounded-lg px-3 py-2 text-sm text-chalk focus:outline-none focus:border-khaki"
          >
            {[1,2,3,4].map(n => (
              <option key={n} value={n}>{n} truck{n > 1 ? 's' : ''}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card">
          <p className="metric-label">Method</p>
          <p className="text-lg font-semibold text-chalk">{summary.routing_method || 'N/A'}</p>
        </div>
        <div className="card">
          <p className="metric-label">Total Stops</p>
          <p className="metric-value">{summary.total_stops || 0}</p>
        </div>
        <div className="card">
          <p className="metric-label">Distance</p>
          <p className="metric-value">{summary.total_distance_km || 0} km</p>
        </div>
        <div className="card">
          <p className="metric-label">Top Hotspot</p>
          <p className="text-lg font-semibold text-signal-red truncate">{summary.top_hotspot || 'N/A'}</p>
        </div>
      </div>

      {/* Response Queue */}
      <div className="card">
        <h2 className="font-heading font-bold text-lg text-chalk mb-4 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-signal-amber" />
          Tiered Response Queue
        </h2>

        <div className="space-y-3">
          {responses.map((resp, i) => (
            <div key={i} className="flex items-center gap-4 p-3 bg-stone/30 rounded-lg">
              <div className={`p-2 rounded-lg ${
                resp.action === 'PRE_POSITION_TOW_TRUCK' ? 'bg-signal-red/20 text-signal-red' :
                resp.action === 'COMMUNITY_MARSHAL' ? 'bg-signal-amber/20 text-signal-amber' :
                'bg-signal-emerald/20 text-signal-emerald'
              }`}>
                {resp.action === 'PRE_POSITION_TOW_TRUCK' ? <Truck className="w-5 h-5" /> :
                 resp.action === 'COMMUNITY_MARSHAL' ? <MapPin className="w-5 h-5" /> :
                 <CheckCircle className="w-5 h-5" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-chalk truncate">{resp.junction}</p>
                <p className="text-xs text-mist/50">{resp.reason}</p>
              </div>
              <span className="text-xs font-mono px-2 py-1 rounded bg-stone/50 text-mist/70 whitespace-nowrap">
                {resp.action.replace(/_/g, ' ')}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Truck Routes */}
      {routes.length > 0 && (
        <div className="card">
          <h2 className="font-heading font-bold text-lg text-chalk mb-4 flex items-center gap-2">
            <Truck className="w-5 h-5 text-khaki" />
            Truck Routes
          </h2>

          <div className="space-y-4">
            {routes.map((route, i) => (
              <div key={i} className="p-4 bg-stone/30 rounded-lg border border-mist/10">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-8 h-8 bg-khaki rounded-lg flex items-center justify-center font-heading font-bold text-asphalt">
                    T{route.truck_id}
                  </div>
                  <div>
                    <p className="font-semibold text-chalk">Truck {route.truck_id}</p>
                    <p className="text-xs text-mist/50">{route.stops.length} stops</p>
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                  {route.stops.map((stop, j) => (
                    <span key={j} className="flex items-center gap-2">
                      <span className="px-2 py-1 bg-khaki/10 text-khaki rounded font-mono text-xs">
                        {stop.lat.toFixed(4)}, {stop.lon.toFixed(4)}
                      </span>
                      {j < route.stops.length - 1 && (
                        <span className="text-mist/30">→</span>
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

function LoadingSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-8 w-48 bg-stone rounded" />
      <div className="grid grid-cols-4 gap-4">
        {[1,2,3,4].map(i => <div key={i} className="card h-20 bg-stone/30" />)}
      </div>
      <div className="card h-48 bg-stone/30" />
    </div>
  )
}
