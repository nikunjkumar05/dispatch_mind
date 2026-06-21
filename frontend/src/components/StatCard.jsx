import { formatNumber } from '../utils/api'

export default function StatCard({ 
  label, 
  value, 
  suffix, 
  sub, 
  icon: Icon,
  // New props for dark theme dashboards
  title,
  change,
  color = 'blue',
  gradient = 'light'
}) {
  // Support both old and new API
  const displayLabel = label || title;
  const displayValue = value;
  const displayIcon = Icon || icon;
  
  const colorClasses = {
    blue: 'from-blue-500 to-cyan-500',
    green: 'from-green-500 to-emerald-500',
    emerald: 'from-emerald-500 to-teal-500',
    orange: 'from-orange-500 to-yellow-500',
    purple: 'from-purple-500 to-pink-500',
    red: 'from-red-500 to-orange-500',
  };
  
  const gradientClass = colorClasses[color] || colorClasses.blue;
  
  if (gradient === 'dark') {
    return (
      <div className="bg-white/10 backdrop-blur-md rounded-xl border border-white/20 p-4 hover:bg-white/15 transition-all">
        <div className="flex items-center gap-3 mb-3">
          <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${gradientClass} flex items-center justify-center`}>
            {displayIcon && <displayIcon className="w-5 h-5 text-white" />}
          </div>
          <div>
            <p className="text-white/70 text-sm">{displayLabel}</p>
            <p className="text-white text-2xl font-bold">{displayValue}</p>
          </div>
        </div>
        {change && (
          <div className={`text-sm ${change.startsWith('+') || change.includes('↓') ? 'text-green-400' : 'text-red-400'}`}>
            {change} from last week
          </div>
        )}
        {sub && <p className="text-xs text-white/50 mt-2">{sub}</p>}
      </div>
    );
  }
  
  return (
    <div className="stat-card">
      <div className="flex items-start justify-between mb-2">
        <span className="metric-label">{displayLabel}</span>
        {displayIcon && <displayIcon className="w-4 h-4 text-muted" />}
      </div>
      <div className="metric-value">
        {typeof displayValue === 'number' ? formatNumber(displayValue) : displayValue}
        {suffix && <span className="text-lg text-muted ml-1">{suffix}</span>}
      </div>
      {sub && <p className="text-xs text-muted mt-1">{sub}</p>}
    </div>
  )
}
