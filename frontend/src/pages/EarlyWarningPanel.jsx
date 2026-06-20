import { useState, useEffect, useCallback } from 'react'
import {
  AlertTriangle, Clock, MapPin, Truck, Activity,
  ChevronRight, RefreshCw, Radio
} from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts'

const REFRESH_INTERVAL = 30_000

const MOCK_TIPPING_DATA = [
  { time: '06:00', weight: 12 }, { time: '06:15', weight: 18 },
  { time: '06:30', weight: 25 }, { time: '06:45', weight: 34 },
  { time: '07:00', weight: 52 }, { time: '07:15', weight: 68 },
  { time: '07:30', weight: 89 }, { time: '07:45', weight: 110 },
  { time: '08:00', weight: 145 }, { time: '08:15', weight: 198 },
  { time: '08:30', weight: 275, tipping: true },
  { time: '08:45', weight: 310 }, { time: '09:00', weight: 290 },
]

function countdownMinutes() {
  const now = new Date()
  const mins = now.getMinutes()
  const secs = now.getSeconds()
  const remaining = 15 - (mins % 15)
  const secsLeft = 60 - secs
  return remaining * 60 + secsLeft
}

function formatCountdown(totalSeconds) {
  const m = Math.floor(totalSeconds / 60)
  const s = totalSeconds % 60
  return `${m} min ${s.toString().padStart(2, '0')} sec`
}

export default function EarlyWarningPanel() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastFetch, setLastFetch] = useState(null)
  const [secondsLeft, setSecondsLeft] = useState(countdownMinutes())

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch('/api/early-warning-system')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      setData(json)
      setLastFetch(new Date())
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const id = setInterval(fetchData, REFRESH_INTERVAL)
    return () => clearInterval(id)
  }, [fetchData])

  useEffect(() => {
    const id = setInterval(() => {
      setSecondsLeft(countdownMinutes())
    }, 1000)
    return () => clearInterval(id)
  }, [])

  const zones = data?.top_risk_zones || []
  const hero = zones[0] || null
  const rest = zones.slice(1)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading font-bold text-2xl text-chalk flex items-center gap-2">
            <Radio className="w-6 h-6 text-signal-red" />
            Phantom Blockage AI
          </h1>
          <p className="text-muted text-sm mt-1">
            Predicting gridlock 15 minutes before it happens
          </p>
        </div>
        <button
          onClick={fetchData}
          className="flex items-center gap-2 px-3 py-1.5 bg-elevated border border-white/[0.08] rounded-lg text-sm text-muted hover:text-chalk hover:border-accent/30 transition-all"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      {/* Status Bar */}
      <div className="flex items-center gap-4 text-xs text-muted">
        <span className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-signal-emerald animate-pulse" />
          Live — {data?.current_time_block || '--:--'}
        </span>
        <span>Next block: {data?.next_time_block || '--:--'}</span>
        {lastFetch && (
          <span>Last: {lastFetch.toLocaleTimeString()}</span>
        )}
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-3 bg-signal-red/10 border border-signal-red/20 rounded-lg text-sm text-signal-red">
          Failed to fetch: {error}. Retrying in {REFRESH_INTERVAL / 1000}s...
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="space-y-4">
          <div className="h-48 bg-elevated rounded-xl animate-pulse" />
          <div className="grid grid-cols-2 gap-3">
            {[1,2,3,4].map(i => (
              <div key={i} className="h-24 bg-elevated rounded-xl animate-pulse" />
            ))}
          </div>
        </div>
      )}

      {/* Hero Card — #1 Risk Zone */}
      {hero && (
        <div className="relative overflow-hidden rounded-xl border border-signal-red/30 bg-gradient-to-br from-signal-red/[0.08] to-surface">
          {/* Pulsing glow */}
          <div className="absolute inset-0 bg-signal-red/[0.04] animate-pulse pointer-events-none" />
          <div className="absolute top-0 right-0 w-40 h-40 bg-signal-red/10 rounded-full blur-3xl pointer-events-none" />

          <div className="relative p-5">
            {/* Top row */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 bg-signal-red text-white text-[10px] font-bold uppercase tracking-wider rounded">
                  PHANTOM BLOCKAGE ALERT
                </span>
                <span className="px-2 py-0.5 bg-signal-red/20 text-signal-red text-[10px] font-bold rounded">
                  #{hero.rank}
                </span>
              </div>
              <div className="text-right">
                <p className="text-[10px] text-muted uppercase tracking-wider">Risk Score</p>
                <p className="font-mono text-2xl font-bold text-signal-red">
                  {hero.phantom_risk_score}
                </p>
              </div>
            </div>

            {/* Countdown */}
            <div className="flex items-center gap-3 mb-4 p-3 bg-black/30 rounded-lg border border-signal-red/20">
              <Clock className="w-5 h-5 text-signal-red animate-pulse shrink-0" />
              <div>
                <p className="text-sm font-medium text-chalk">
                  Gridlock predicted in {formatCountdown(secondsLeft)}
                </p>
                <p className="text-xs text-muted mt-0.5">
                  Window closes at {data?.next_time_block}
                </p>
              </div>
            </div>

            {/* Details Grid */}
            <div className="grid grid-cols-3 gap-3 mb-4">
              <div className="p-3 bg-black/20 rounded-lg">
                <p className="text-[10px] text-muted uppercase tracking-wider">Vehicle</p>
                <p className="text-sm font-medium text-chalk mt-0.5">{hero.vehicle_type}</p>
                <p className="text-xs text-muted">Weight: {hero.weight}</p>
              </div>
              <div className="p-3 bg-black/20 rounded-lg">
                <p className="text-[10px] text-muted uppercase tracking-wider">Location</p>
                <p className="text-sm font-mono text-chalk mt-0.5">
                  {hero.latitude}, {hero.longitude}
                </p>
              </div>
              <div className="p-3 bg-black/20 rounded-lg">
                <p className="text-[10px] text-muted uppercase tracking-wider">Seeds Nearby</p>
                <p className="text-sm font-mono text-chalk mt-0.5">{hero.nearby_seed_count}</p>
                <p className="text-xs text-muted">within {hero.avg_distance_to_seeds}m</p>
              </div>
            </div>

            {/* Recommended Action */}
            <div className="p-3 bg-signal-red/10 border border-signal-red/20 rounded-lg">
              <p className="text-[10px] text-signal-red font-bold uppercase tracking-wider mb-1">
                Recommended Action
              </p>
              <p className="text-sm text-chalk leading-relaxed">
                {hero.recommended_action}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* No Data */}
      {!loading && !hero && (
        <div className="text-center py-12 card">
          <Activity className="w-10 h-10 text-signal-emerald mx-auto mb-3" />
          <p className="text-chalk font-medium">No phantom risk detected</p>
          <p className="text-sm text-muted mt-1">Current time blocks are clear</p>
        </div>
      )}

      {/* Remaining Zones */}
      {rest.length > 0 && (
        <div>
          <h2 className="text-sm font-medium text-muted uppercase tracking-wider mb-3 flex items-center gap-2">
            <AlertTriangle className="w-3.5 h-3.5" />
            Additional Risk Zones ({rest.length})
          </h2>
          <div className="space-y-2">
            {rest.map((zone) => (
              <ZoneCard key={zone.rank} zone={zone} />
            ))}
          </div>
        </div>
      )}

      {/* Tipping Point Forecast */}
      <TippingPointChart junction={hero?.junction_node || 'BTP044'} />
    </div>
  )
}

function ZoneCard({ zone }) {
  return (
    <div className="card border border-white/[0.06] hover:border-signal-red/20 transition-colors group">
      <div className="flex items-center gap-4">
        {/* Rank */}
        <div className="w-10 h-10 rounded-lg bg-elevated flex items-center justify-center shrink-0">
          <span className="font-mono text-lg font-bold text-muted group-hover:text-signal-red transition-colors">
            {zone.rank}
          </span>
        </div>

        {/* Details */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Truck className="w-3.5 h-3.5 text-muted" />
            <span className="text-sm font-medium text-chalk">{zone.vehicle_type}</span>
            <span className="text-xs text-muted">wt. {zone.weight}</span>
            <span className="text-[10px] text-muted">·</span>
            <span className="text-xs text-muted">{zone.nearby_seed_count} seeds within {zone.avg_distance_to_seeds}m</span>
          </div>
          <p className="text-xs text-muted truncate">{zone.recommended_action}</p>
        </div>

        {/* Score + Arrow */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="text-right">
            <p className="text-[10px] text-muted uppercase tracking-wider">Score</p>
            <p className="font-mono text-lg font-bold text-tier-high">
              {zone.phantom_risk_score}
            </p>
          </div>
          <ChevronRight className="w-4 h-4 text-muted group-hover:text-signal-red transition-colors" />
        </div>
      </div>
    </div>
  )
}

function TippingPointChart({ junction }) {
  const tippingBlock = MOCK_TIPPING_DATA.find(d => d.tipping)

  return (
    <div className="card border border-white/[0.06]">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-medium text-chalk flex items-center gap-2">
            <Activity className="w-4 h-4 text-signal-amber" />
            Tipping Point Forecast
          </h3>
          <p className="text-xs text-muted mt-0.5">
            {junction} — Morning congestion build-up
          </p>
        </div>
        {tippingBlock && (
          <span className="px-2 py-0.5 bg-signal-red/10 text-signal-red text-[10px] font-bold rounded uppercase">
            Tipping: {tippingBlock.time}
          </span>
        )}
      </div>

      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={MOCK_TIPPING_DATA} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis
              dataKey="time"
              tick={{ fontSize: 10, fill: '#6B7280' }}
              axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 10, fill: '#6B7280' }}
              axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1F2937',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '8px',
                fontSize: '12px',
                color: '#F9FAFB',
              }}
              formatter={(value) => [`${value}`, 'Congestion Weight']}
            />
            {tippingBlock && (
              <ReferenceLine
                x={tippingBlock.time}
                stroke="#EF4444"
                strokeDasharray="4 4"
                strokeWidth={2}
                label={{
                  value: 'TIPPING POINT',
                  position: 'top',
                  fill: '#EF4444',
                  fontSize: 10,
                  fontWeight: 'bold',
                }}
              />
            )}
            <Line
              type="monotone"
              dataKey="weight"
              stroke="#3B82F6"
              strokeWidth={2}
              dot={{ r: 3, fill: '#3B82F6' }}
              activeDot={{ r: 5, stroke: '#F9FAFB', strokeWidth: 2 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 mt-3 text-[10px] text-muted">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-accent rounded" />
          Congestion Weight
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-signal-red rounded border-dashed" />
          Tipping Point
        </span>
      </div>
    </div>
  )
}
