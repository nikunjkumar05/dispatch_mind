import { useState, useEffect } from 'react'
import { useApi } from '../utils/api'
import { Shield, TriangleAlert as AlertTriangle, TrendingDown, Users, Zap, Activity, RefreshCw, Radio, Car, CircleCheck as CheckCircle, Clock, Volume2 } from 'lucide-react'
import ErrorState from '../components/ErrorState'

export default function CommandCenter() {
  const { data, loading, error, refetch } = useApi('/capacity-status')
  const { data: causalData } = useApi('/causal-impact')
  const [tickerItems, setTickerItems] = useState([])
  const [tickerPaused, setTickerPaused] = useState(false)

  // Simulated live operations ticker
  useEffect(() => {
    const tickerEvents = [
      { type: 'cleared', junction: 'BTP044', officer: 'Kumar', vehicles: 3, time: 'Just now' },
      { type: 'dispatched', junction: 'BTP067', officer: 'Singh', time: '2 min ago' },
      { type: 'alert', junction: 'BTP089', message: 'Capacity restored to 72%', time: '5 min ago' },
      { type: 'cleared', junction: 'BTP102', officer: 'Patel', vehicles: 2, time: '8 min ago' },
      { type: 'predicted', junction: 'BTP148', time: '15 min ago', message: 'Tipping point predicted' },
    ]
    setTickerItems(tickerEvents)

    // Simulate new events arriving (in real implementation, this would be Supabase Realtime)
    const interval = setInterval(() => {
      if (!tickerPaused) {
        const newEvents = [
          { type: 'cleared', junction: `BTP${Math.floor(Math.random() * 200)}`, officer: 'Sharma', vehicles: Math.floor(Math.random() * 5) + 1, time: 'Just now' },
          { type: 'dispatched', junction: `BTP${Math.floor(Math.random() * 200)}`, officer: 'Verma', time: 'Just now' },
          { type: 'alert', junction: `BTP${Math.floor(Math.random() * 200)}`, message: 'New violation detected', time: 'Just now' },
        ]
        const newItem = newEvents[Math.floor(Math.random() * newEvents.length)]
        setTickerItems(prev => [newItem, ...prev.slice(0, 9)])
      }
    }, 30000) // Every 30 seconds

    return () => clearInterval(interval)
  }, [tickerPaused])

  if (loading) return <PageSkeleton />
  if (error) return <ErrorState message={error} onRetry={refetch} />

  const summary = data?.summary || {}
  const junctions = data?.junctions || []
  const model = causalData?.model || {}

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading font-bold text-2xl text-chalk flex items-center gap-2">
            <Shield className="w-6 h-6 text-accent" />
            Command Center
          </h1>
          <p className="text-muted text-sm mt-1">ACP/DCP view — Top 5 enforcement zones</p>
        </div>
        <button
          onClick={refetch}
          className="flex items-center gap-2 px-3 py-2 bg-elevated rounded-lg text-sm text-muted hover:text-chalk transition-colors"
        >
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {/* Live Operations Ticker */}
      <div className="card border border-accent/20 bg-accent/5 overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2 border-b border-accent/20 bg-accent/10">
          <div className="flex items-center gap-2">
            <Radio className="w-4 h-4 text-accent animate-pulse" />
            <span className="text-xs font-bold text-accent uppercase tracking-wider">Live Operations</span>
          </div>
          <button
            onClick={() => setTickerPaused(!tickerPaused)}
            className="text-xs text-muted hover:text-chalk"
          >
            {tickerPaused ? 'Resume' : 'Pause'}
          </button>
        </div>
        <div className="max-h-40 overflow-y-auto">
          {tickerItems.map((item, idx) => (
            <div
              key={idx}
              className="flex items-center gap-3 px-4 py-2 border-b border-white/[0.04] last:border-0 hover:bg-elevated/30 transition-colors"
            >
              {item.type === 'cleared' && (
                <CheckCircle className="w-4 h-4 text-signal-emerald shrink-0" />
              )}
              {item.type === 'dispatched' && (
                <Car className="w-4 h-4 text-accent shrink-0" />
              )}
              {item.type === 'alert' && (
                <AlertTriangle className="w-4 h-4 text-signal-amber shrink-0" />
              )}
              {item.type === 'predicted' && (
                <Zap className="w-4 h-4 text-signal-red shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <p className="text-xs text-chalk truncate">
                  {item.type === 'cleared' && `${item.junction} cleared — ${item.vehicles} vehicles towed by ${item.officer}`}
                  {item.type === 'dispatched' && `${item.officer} dispatched to ${item.junction}`}
                  {item.type === 'alert' && `${item.junction}: ${item.message}`}
                  {item.type === 'predicted' && `${item.junction}: ${item.message}`}
                </p>
              </div>
              <span className="text-[10px] text-muted shrink-0">{item.time}</span>
            </div>
          ))}
        </div>
      </div>

      {/* City Capacity Banner */}
      <div className="card border-accent/20 bg-accent/5">
        <p className="text-xs uppercase tracking-wider text-accent font-semibold mb-3">City Road Capacity Status</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <CapacityGauge
            label="RED (Bottleneck)"
            value={summary.red_junctions || 0}
            color="bg-signal-red"
            textColor="text-signal-red"
          />
          <CapacityGauge
            label="YELLOW (Degraded)"
            value={summary.yellow_junctions || 0}
            color="bg-signal-amber"
            textColor="text-signal-amber"
          />
          <CapacityGauge
            label="GREEN (Normal)"
            value={summary.green_junctions || 0}
            color="bg-signal-emerald"
            textColor="text-signal-emerald"
          />
          <CapacityGauge
            label="Avg Capacity Loss"
            value={`${summary.avg_capacity_loss_pct || 0}%`}
            color="bg-accent"
            textColor="text-accent"
          />
        </div>
      </div>

      {/* Causal Proof */}
      {model.status === 'success' && (
        <div className="card border-signal-emerald/20 bg-signal-emerald/5">
          <p className="text-xs uppercase tracking-wider text-signal-emerald font-semibold mb-2">
            Causal Proof — Validated
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <p className="font-mono text-2xl font-bold text-chalk">R² = {model.r2_score}</p>
              <p className="text-xs text-muted">Regression Accuracy</p>
            </div>
            <div>
              <p className="font-mono text-2xl font-bold text-chalk">
                {model.speed_drop_per_1pct_capacity_loss_kmh} km/h
              </p>
              <p className="text-xs text-muted">Speed Drop per 1% Capacity Loss</p>
            </div>
            <div>
              <p className="font-mono text-2xl font-bold text-chalk">
                {'>'} {model.threshold_for_12kph_drop_pct}%
              </p>
              <p className="text-xs text-muted">Capacity Loss → 12 km/h Drop</p>
            </div>
          </div>
        </div>
      )}

      {/* Top 5 Clear Now */}
      <div className="card">
        <h2 className="font-heading font-semibold text-lg text-chalk mb-4 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-signal-red" />
          Top 5 — Clear Now
        </h2>
        <div className="space-y-2">
          {junctions.slice(0, 5).map((j, i) => (
            <div key={i} className="flex items-center gap-4 p-3 bg-elevated rounded-xl">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-mono font-bold text-sm ${
                j.status === 'RED' ? 'bg-signal-red text-white' :
                j.status === 'YELLOW' ? 'bg-signal-amber text-black' :
                'bg-signal-emerald text-white'
              }`}>
                {i + 1}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-chalk text-sm truncate">{j.junction}</p>
                <p className="text-xs text-muted">{j.violation_count} violations · {j.footpath_violations} footpath</p>
              </div>
              <div className="text-right">
                <p className={`font-mono font-bold text-lg ${
                  j.capacity_loss_pct > 50 ? 'text-signal-red' :
                  j.capacity_loss_pct > 30 ? 'text-signal-amber' : 'text-signal-emerald'
                }`}>
                  {j.capacity_loss_pct}%
                </p>
                <p className="text-[10px] text-muted uppercase">capacity loss</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          icon={<Users className="w-4 h-4" />}
          label="Footpath Violations"
          value={summary.total_footpath_violations || 0}
          color="text-signal-amber"
        />
        <MetricCard
          icon={<TrendingDown className="w-4 h-4" />}
          label="Pedestrian Spillover"
          value={`${summary.total_pedestrian_spillover_m || 0}m`}
          color="text-tier-high"
        />
        <MetricCard
          icon={<Activity className="w-4 h-4" />}
          label="Junctions Analyzed"
          value={summary.total_junctions || 0}
          color="text-accent"
        />
        <MetricCard
          icon={<Zap className="w-4 h-4" />}
          label="Worst Junction"
          value={summary.worst_capacity_loss_pct ? `${summary.worst_capacity_loss_pct}%` : 'N/A'}
          color="text-signal-red"
        />
      </div>
    </div>
  )
}

function CapacityGauge({ label, value, color, textColor }) {
  return (
    <div className="text-center">
      <div className={`w-16 h-16 mx-auto rounded-full ${color} flex items-center justify-center mb-2`}>
        <span className="font-mono font-bold text-xl text-white">{value}</span>
      </div>
      <p className="text-[10px] text-muted uppercase tracking-wider">{label}</p>
    </div>
  )
}

function MetricCard({ icon, label, value, color }) {
  return (
    <div className="card">
      <div className={`flex justify-center mb-1 ${color}`}>{icon}</div>
      <p className="font-mono font-bold text-xl text-chalk text-center">{value}</p>
      <p className="text-[10px] text-muted text-center uppercase tracking-wider">{label}</p>
    </div>
  )
}

function PageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-48 bg-elevated rounded-lg animate-pulse" />
      <div className="card h-32 bg-elevated animate-pulse" />
      <div className="card h-48 bg-elevated animate-pulse" />
    </div>
  )
}
