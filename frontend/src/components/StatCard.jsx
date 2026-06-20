import { formatNumber } from '../utils/api'

export default function StatCard({ label, value, suffix, sub, icon: Icon }) {
  return (
    <div className="stat-card">
      <div className="flex items-start justify-between mb-2">
        <span className="metric-label">{label}</span>
        {Icon && <Icon className="w-4 h-4 text-muted" />}
      </div>
      <div className="metric-value">
        {typeof value === 'number' ? formatNumber(value) : value}
        {suffix && <span className="text-lg text-muted ml-1">{suffix}</span>}
      </div>
      {sub && <p className="text-xs text-muted mt-1">{sub}</p>}
    </div>
  )
}
