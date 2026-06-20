import { useState } from 'react'
import { useApi, formatDelay, tierColor } from '../utils/api'
import { AlertTriangle, Clock, Car, MapPin, ChevronRight } from 'lucide-react'

export default function PriorityQueue({ role }) {
  const [station, setStation] = useState('ALL')
  const { data: stations } = useApi('/stations')
  const { data, loading } = useApi(`/priority-queue/${station}`, [station])

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
          <p className="text-mist/50 text-sm mt-1">
            {role === 'constable' 
              ? 'Your top 5 clearance targets — sorted by congestion damage'
              : 'Station-wide enforcement priorities'}
          </p>
        </div>

        <select
          value={station}
          onChange={(e) => setStation(e.target.value)}
          className="bg-stone/50 border border-mist/20 rounded-lg px-4 py-2 text-sm text-chalk focus:outline-none focus:border-khaki"
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
      ) : (
        <div className="space-y-4">
          {data?.cards?.map((card) => (
            <div 
              key={card.junction} 
              className={`priority-card ${card.tier.toLowerCase()}`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span 
                      className="font-heading font-bold text-3xl"
                      style={{ color: tierColor(card.tier) }}
                    >
                      #{card.rank}
                    </span>
                    <div>
                      <h3 className="font-heading font-bold text-lg text-chalk">
                        {card.junction}
                      </h3>
                      <p className="text-xs text-mist/50">{card.station}</p>
                    </div>
                    <span className={`tier-badge ${card.tier}`}>{card.tier}</span>
                  </div>

                  <div className="flex flex-wrap gap-4 text-sm">
                    <div className="flex items-center gap-1.5 text-mist/70">
                      <Clock className="w-4 h-4" />
                      <span className="font-mono font-semibold text-chalk">
                        {formatDelay(card.total_delay)}
                      </span>
                      <span>delay</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-mist/70">
                      <Car className="w-4 h-4" />
                      <span className="font-mono font-semibold text-chalk">
                        {card.violation_count}
                      </span>
                      <span>violations</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-mist/70">
                      <MapPin className="w-4 h-4" />
                      <span>{card.top_vehicle}</span>
                    </div>
                  </div>

                  <p className="text-xs text-mist/40 mt-2 italic">
                    {card.explanation}
                  </p>
                </div>

                {/* Map link */}
                <a
                  href={`https://www.google.com/maps?q=${card.lat},${card.lon}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-2 rounded-lg hover:bg-stone/50 transition-colors"
                  title="Open in Maps"
                >
                  <ChevronRight className="w-5 h-5 text-mist/40" />
                </a>
              </div>
            </div>
          ))}

          {data?.cards?.length === 0 && (
            <div className="card text-center py-8">
              <p className="text-mist/50">No violations found for this station</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
