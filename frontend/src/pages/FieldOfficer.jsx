import { useState, useEffect } from 'react'
import { useApi } from '../utils/api'
import { MapPin, Truck, CircleCheck as CheckCircle, TriangleAlert as AlertTriangle, Navigation, ExternalLink, Volume2, VolumeX } from 'lucide-react'
import ErrorState from '../components/ErrorState'

export default function FieldOfficer() {
  const [selectedViolation, setSelectedViolation] = useState(null)
  const [voiceEnabled, setVoiceEnabled] = useState(false)
  const [lastSpoken, setLastSpoken] = useState(null)
  const { data, loading, error, refetch } = useApi('/priority-queue/ALL?top_n=5')

  // Voice alert for top violation
  useEffect(() => {
    if (!voiceEnabled || !data?.cards?.length) return

    const topCard = data.cards[0]
    const message = `Attention. Priority ${topCard.tier}. ${topCard.junction}. ${topCard.violation_count} violations. ${topCard.total_delay} vehicle minutes delay. Top vehicle type: ${topCard.top_vehicle}.`

    // Only speak if different from last message
    if (lastSpoken !== message) {
      speakAlert(message)
      setLastSpoken(message)
    }
  }, [data, voiceEnabled, lastSpoken])

  const speakAlert = (text) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel() // Cancel any ongoing speech
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.rate = 0.9
      utterance.pitch = 1
      utterance.volume = 1
      window.speechSynthesis.speak(utterance)
    }
  }

  const speakViolation = (card) => {
    const text = `${card.junction}. Priority ${card.tier}. Gridlock score ${card.gridlock_score}. ${card.violation_count} violations recorded. ${card.top_vehicle} is the most common vehicle type.`
    speakAlert(text)
  }

  if (loading) return <PageSkeleton />
  if (error) return <ErrorState message={error} onRetry={refetch} />

  const cards = data?.cards || []

  return (
    <div className="space-y-4">
      {/* Header — Minimal for mobile */}
      <div className="flex items-center justify-between">
        <h1 className="font-heading font-bold text-xl text-chalk flex items-center gap-2">
          <MapPin className="w-5 h-5 text-signal-emerald" />
          Field Dispatch
        </h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setVoiceEnabled(!voiceEnabled)}
            className={`p-2 rounded-lg transition-colors ${
              voiceEnabled
                ? 'bg-accent text-white'
                : 'bg-elevated text-muted'
            }`}
            title={voiceEnabled ? 'Disable voice alerts' : 'Enable voice alerts'}
          >
            {voiceEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
          </button>
          <button
            onClick={refetch}
            className="px-3 py-1.5 bg-elevated rounded-lg text-xs text-muted"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Voice Mode Banner */}
      {voiceEnabled && (
        <div className="flex items-center gap-2 p-3 bg-accent/10 border border-accent/20 rounded-lg text-xs text-accent">
          <Volume2 className="w-4 h-4 animate-pulse" />
          Voice alerts enabled — Hands-free operation mode active
        </div>
      )}

      <p className="text-xs text-muted">Tap a violation → Go to location → Tow → Done</p>

      {/* Violation Cards — Large touch targets for mobile */}
      <div className="space-y-3">
        {cards.map((card, i) => (
          <div
            key={i}
            onClick={() => setSelectedViolation(selectedViolation === i ? null : i)}
            className={`p-4 rounded-xl border cursor-pointer transition-all ${
              selectedViolation === i
                ? 'bg-accent/10 border-accent/30'
                : 'bg-elevated border-white/[0.06] active:bg-elevated/80'
            }`}
          >
            {/* Priority Badge + Junction */}
            <div className="flex items-center gap-3 mb-3">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-mono font-bold text-lg ${
                i === 0 ? 'bg-signal-red text-white' :
                i === 1 ? 'bg-tier-high text-white' :
                'bg-signal-amber text-black'
              }`}>
                {i + 1}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-chalk text-sm truncate">{card.junction}</p>
                <p className="text-xs text-muted">{card.tier} · {card.top_vehicle}</p>
              </div>
              <div className="text-right">
                <p className="font-mono font-bold text-lg text-signal-red">{card.total_delay}</p>
                <p className="text-[10px] text-muted">veh-min</p>
              </div>
            </div>

            {/* Expanded Details */}
            {selectedViolation === i && (
              <div className="space-y-3 pt-3 border-t border-white/[0.06]">
                {/* Voice Button */}
                {voiceEnabled && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      speakViolation(card)
                    }}
                    className="flex items-center justify-center gap-2 w-full py-2 bg-accent/20 text-accent rounded-lg text-sm font-medium"
                  >
                    <Volume2 className="w-4 h-4" />
                    Read Aloud
                  </button>
                )}

                {/* Action Button — One Tap */}
                <a
                  href={`https://www.google.com/maps?q=${card.lat},${card.lon}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-2 w-full py-3 bg-signal-emerald rounded-xl text-white font-semibold text-sm active:bg-signal-emerald/80"
                  onClick={(e) => e.stopPropagation()}
                >
                  <Navigation className="w-4 h-4" />
                  Navigate to Location
                </a>

                {/* Info */}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2 bg-base rounded-lg">
                    <p className="text-muted">Gridlock Score</p>
                    <p className="font-mono font-bold text-chalk">{card.gridlock_score}</p>
                  </div>
                  <div className="p-2 bg-base rounded-lg">
                    <p className="text-muted">Violations</p>
                    <p className="font-mono font-bold text-chalk">{card.violation_count}</p>
                  </div>
                  <div className="p-2 bg-base rounded-lg">
                    <p className="text-muted">Coordinates</p>
                    <p className="font-mono text-chalk">{card.lat}, {card.lon}</p>
                  </div>
                  <div className="p-2 bg-base rounded-lg">
                    <p className="text-muted">Station</p>
                    <p className="font-mono text-chalk">{card.station}</p>
                  </div>
                </div>

                {/* Explanation */}
                <p className="text-xs text-muted p-2 bg-base rounded-lg">{card.explanation}</p>

                {/* Officer Confirmation */}
                <div className="flex gap-2">
                  <button className="flex-1 py-2 bg-signal-emerald/20 text-signal-emerald rounded-lg text-xs font-semibold">
                    Towed
                  </button>
                  <button className="flex-1 py-2 bg-signal-amber/20 text-signal-amber rounded-lg text-xs font-semibold">
                    Warned
                  </button>
                  <button className="flex-1 py-2 bg-signal-red/20 text-signal-red rounded-lg text-xs font-semibold">
                    Not Found
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {cards.length === 0 && (
        <div className="card text-center py-8">
          <CheckCircle className="w-12 h-12 text-signal-emerald mx-auto mb-3" />
          <p className="text-chalk font-semibold">All Clear</p>
          <p className="text-muted text-sm">No priority violations at this time</p>
        </div>
      )}
    </div>
  )
}

function PageSkeleton() {
  return (
    <div className="space-y-4">
      <div className="h-8 w-48 bg-elevated rounded-lg animate-pulse" />
      {[1,2,3].map(i => (
        <div key={i} className="h-32 bg-elevated rounded-xl animate-pulse" />
      ))}
    </div>
  )
}
