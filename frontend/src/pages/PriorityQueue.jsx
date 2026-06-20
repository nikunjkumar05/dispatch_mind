import { useState } from 'react'
import { useApi, formatDelay, tierColor } from '../utils/api'
import { AlertTriangle, Clock, Car, MapPin, ExternalLink } from 'lucide-react'
import ErrorState from '../components/ErrorState'
import TierBadge from '../components/TierBadge'

export default function PriorityQueue({ role }) {
  const [station, setStation] = useState('ALL')
  const { data: stations } = useApi('/stations')
  const { data, loading, error, refetch } = useApi(`/priority-queue/${station}`, [station])

  const stationList = stations?.stations || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-heading font-bold text-2xl text-chalk flex items-center gap-2">
            <AlertTriangle className="w-6 h-6 text-signal-red" />
            Priority Queue
          </h1>
          <p className="text-muted text-sm mt-1">
            {role === 'constable' 
              ? 'Your top 5 clearance targets — sorted by congestion damage'
              : 'Station-wide enforcement priorities'}
          </p>
        </div>

        <select
          value={station}
          onChange={(e) => setStation(e.target.value)}
          className="bg-elevated border border-white/[0.08] rounded-lg px-4 py-2 text-sm text-chalk focus:outline-none focus:border-accent/50 transition-colors"
        >
          <option value="ALL">All Stations</option>
          {stationList.map(s => (
            <option key={s.station} value={s.station}>{s.station}</option>
          ))}
        </select>
      </div>

      {/* Priority Cards */}
      {loading ? (
        <div className="space-y-4">
          {[1,2,3,4,5].map(i => (
            <div key={i} className="priority-card medium animate-pulse h-28" />
          ))}
        </div>
      ) : error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : (
        <div className="space-y-4">
          {data?.cards?.map((card) => (
            <div 
              key={card.junction} 
              className={`priority-card ${card.tier.toLowerCase()}`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-3">
                    <span 
                      className="font-mono font-bold text-3xl shrink-0"
                      style={{ color: tierColor(card.tier) }}
                    >
                      #{card.rank}
                    </span>
                    <div className="min-w-0">
                      <h3 className="font-heading font-semibold text-base text-chalk truncate">
                        {card.junction}
                      </h3>
                      <p className="text-xs text-muted truncate">{card.station}</p>
                    </div>
                    <TierBadge tier={card.tier} />
                  </div>

                  <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
                    <div className="flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-muted" />
                      <span className="font-mono font-semibold text-chalk">
                        {formatDelay(card.total_delay)}
                      </span>
                      <span className="text-muted">delay</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Car className="w-3.5 h-3.5 text-muted" />
                      <span className="font-mono font-semibold text-chalk">
                        {card.violation_count}
                      </span>
                      <span className="text-muted">violations</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <MapPin className="w-3.5 h-3.5 text-muted" />
                      <span className="text-chalk">{card.top_vehicle}</span>
                    </div>
                  </div>

                  {card.explanation && (
                    <p className="text-xs text-muted mt-3 leading-relaxed">
                      {card.explanation}
                    </p>
                  )}
                </div>

                <a 
                  href={`https://www.google.com/maps?q=${card.lat},${card.lon}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-2 rounded-lg hover:bg-elevated transition-colors shrink-0"
                  title="Open in Maps"
                >
                  <ExternalLink className="w-4 h-4 text-muted" />
                </a>
              </div>
            </div>
          ))}

          {data?.cards?.length === 0 && (
            <div className="card text-center py-12">
              <MapPin className="w-10 h-10 text-muted mx-auto mb-3" />
              <p className="text-muted">No violations found for this station</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
