import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { mappls } from 'mappls-web-maps'
import { useApi, tierColor } from '../utils/api'
import { MapPin, Layers, X, AlertTriangle, Bot, Navigation } from 'lucide-react'
import ErrorState from '../components/ErrorState'
import TierBadge from '../components/TierBadge'

const MAPPLS_KEY = import.meta.env.VITE_MAPPLS_API_KEY
const MAP_ID = 'dispatchmind-map'

export default function MapView() {
  const navigate = useNavigate()
  const { data, loading, error, refetch } = useApi('/map-data')
  const [showSpillover, setShowSpillover] = useState(false)
  const { data: spilloverData, loading: spilloverLoading } = useApi(
    '/spillover-zones',
    [],
    { enabled: showSpillover }
  )
  const [selectedViolation, setSelectedViolation] = useState(null)
  const [selectedZone, setSelectedZone] = useState(null)
  const [mapReady, setMapReady] = useState(false)
  const [mapError, setMapError] = useState(null)
  const mapInstanceRef = useRef(null)
  const markersRef = useRef([])
  const spilloverRef = useRef([])
  const mapplsRef = useRef(null)
  const initRef = useRef(false)

  useEffect(() => {
    if (initRef.current) return
    initRef.current = true

    if (!MAPPLS_KEY) {
      setMapError('Mappls API key not configured')
      return
    }

    try {
      const mapplsClass = new mappls()
      mapplsRef.current = mapplsClass

      mapplsClass.initialize(MAPPLS_KEY, { map: true, plugins: [] }, () => {
        try {
          if (!window.mappls?.Map) {
            setMapError('Mappls SDK failed to load')
            return
          }

          const map = new window.mappls.Map(MAP_ID, {
            center: { lat: 12.9716, lng: 77.5946 },
            zoom: 12,
            search: false,
            location: false,
          })

          map.addListener('load', () => {
            mapInstanceRef.current = map
            setMapReady(true)
          })
        } catch (e) {
          console.error('Mappls Map init failed:', e)
          setMapError('Failed to initialize map')
        }
      })
    } catch (e) {
      console.error('Mappls SDK init failed:', e)
      setMapError('Failed to load map SDK')
    }

    return () => {
      initRef.current = false
      markersRef.current.forEach(m => { try { m.remove() } catch(e) {} })
      markersRef.current = []
      spilloverRef.current.forEach(m => { try { m.remove() } catch(e) {} })
      spilloverRef.current = []
      if (mapInstanceRef.current) {
        try { mapInstanceRef.current.remove() } catch(e) {}
        mapInstanceRef.current = null
      }
      setMapReady(false)
    }
  }, [])

  useEffect(() => {
    if (!mapReady || !mapInstanceRef.current || !mapplsRef.current || !data) return

    const map = mapInstanceRef.current
    markersRef.current.forEach(m => { try { m.remove() } catch(e) {} })
    markersRef.current = []

    data.violations.forEach(v => {
      const marker = new window.mappls.Marker({
        map,
        position: { lat: v.latitude, lng: v.longitude },
        icon: createCircleIcon(tierColor(v.impact_tier), Math.max(5, Math.min(14, v.gridlock_score / 10))),
      })
      if (marker) {
        marker.addListener('click', () => setSelectedViolation(v))
        markersRef.current.push(marker)
      }
    })

    data.junctions.forEach(j => {
      const marker = new window.mappls.Marker({
        map,
        position: { lat: j.lat, lng: j.lon },
        icon: createCircleIcon('#3B82F6', 14, true),
      })
      if (marker) markersRef.current.push(marker)
    })
  }, [mapReady, data])

  useEffect(() => {
    const map = mapInstanceRef.current
    if (!mapReady || !map) return

    spilloverRef.current.forEach(m => { try { m.remove() } catch(e) {} })
    spilloverRef.current = []
    setSelectedZone(null)

    if (!showSpillover || !spilloverData?.zones?.length) return

    const spilloverIcon = createSpilloverIcon()
    spilloverData.zones.forEach(zone => {
      const circle = new window.mappls.Circle({
        map,
        center: { lat: zone.center_lat, lng: zone.center_lon },
        radius: 200,
        strokeColor: '#a855f7',
        strokeOpacity: 0.8,
        strokeWeight: 2,
        fillColor: '#a855f7',
        fillOpacity: 0.3,
      })
      if (circle) {
        circle.addListener('click', () => setSelectedZone(zone))
        spilloverRef.current.push(circle)
      }

      const marker = new window.mappls.Marker({
        map,
        position: { lat: zone.center_lat, lng: zone.center_lon },
        icon: spilloverIcon,
      })
      if (marker) {
        marker.addListener('click', () => setSelectedZone(zone))
        spilloverRef.current.push(marker)
      }
    })
  }, [mapReady, showSpillover, spilloverData])

  if (mapError) {
    return (
      <div className="flex items-center justify-center h-[70vh]">
        <ErrorState message={mapError} />
      </div>
    )
  }

  if (error) {
    return <ErrorState message={error} onRetry={refetch} />
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[70vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
          <p className="text-muted text-sm">Loading tactical map...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-heading font-bold text-2xl text-chalk flex items-center gap-2">
            <MapPin className="w-6 h-6 text-signal-emerald" />
            Tactical Map
          </h1>
          <p className="text-muted text-sm mt-1">
            Violation hotspots across Bengaluru
          </p>
        </div>
        <div className="text-xs text-muted flex items-center gap-1">
          <Layers className="w-3 h-3" />
          Powered by MapmyIndia
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={() => setShowSpillover(value => !value)}
          className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm transition-all ${
            showSpillover
              ? 'bg-[#a855f7]/10 border-[#a855f7]/30 text-[#c084fc]'
              : 'bg-elevated border-white/[0.08] text-muted hover:text-chalk hover:border-accent/30'
          }`}
        >
          <Bot className="w-3.5 h-3.5" />
          {spilloverLoading ? 'Loading spillover...' : showSpillover ? 'Hide Spillover Zones' : 'Show Spillover Zones'}
        </button>
      </div>

      {/* Map */}
      <div className="relative">
        <div
          id={MAP_ID}
          className="w-full rounded-xl overflow-hidden border border-white/[0.06]"
          style={{ height: '70vh', width: '100%' }}
        />

        {/* Legend */}
        <div className="absolute bottom-4 left-4 z-[1000] bg-base/90 backdrop-blur-sm border border-white/[0.08] rounded-xl p-3">
          <p className="text-[10px] font-semibold text-muted uppercase tracking-wider mb-2">Impact Tier</p>
          <div className="space-y-1.5">
            {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(tier => (
              <div key={tier} className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: tierColor(tier) }} />
                <span className="text-xs text-muted">{tier}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Marker Types */}
        <div className="absolute bottom-4 right-4 z-[1000] bg-base/90 backdrop-blur-sm border border-white/[0.08] rounded-xl p-3">
          <p className="text-[10px] font-semibold text-muted uppercase tracking-wider mb-2">Markers</p>
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full border-2 border-accent bg-transparent" />
              <span className="text-xs text-muted">Junction (BTP)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full bg-signal-red" />
              <span className="text-xs text-muted">Violation</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full border-2 border-dashed" style={{ borderColor: '#a855f7', backgroundColor: 'rgba(168,85,247,0.3)' }} />
              <span className="text-xs text-muted">AI Spillover Zone</span>
            </div>
          </div>
        </div>
      </div>

      {/* Selected Violation Detail */}
      {selectedViolation && (
        <div className="card border-accent/20 relative">
          <button 
            onClick={() => setSelectedViolation(null)}
            className="absolute top-3 right-3 p-1 rounded-lg hover:bg-elevated transition-colors"
          >
            <X className="w-4 h-4 text-muted" />
          </button>
          
          <div className="flex items-start gap-4">
            <div className="p-2 rounded-lg bg-signal-red/10">
              <AlertTriangle className="w-5 h-5 text-signal-red" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-2">
                <h3 className="font-heading font-semibold text-base text-chalk truncate">
                  {selectedViolation.mapped_junction}
                </h3>
                <TierBadge tier={selectedViolation.impact_tier} />
              </div>
              <div className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
                <span className="text-muted">
                  Vehicle: <span className="font-mono text-chalk">{selectedViolation.vehicle_type}</span>
                </span>
                <span className="text-muted">
                  Delay: <span className="font-mono text-chalk">{selectedViolation.duration_minutes} min</span>
                </span>
                <span className="text-muted">
                  Score: <span className="font-mono text-chalk">{selectedViolation.gridlock_score}</span>
                </span>
              </div>
              <p className="text-xs text-muted mt-2">
                {selectedViolation.police_station} — {selectedViolation.single_violation}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Selected Spillover Zone Detail */}
      {selectedZone && (
        <div className="card border-[#a855f7]/20 relative" style={{ boxShadow: '0 0 20px rgba(168,85,247,0.1)' }}>
          <button 
            onClick={() => setSelectedZone(null)}
            className="absolute top-3 right-3 p-1 rounded-lg hover:bg-elevated transition-colors"
          >
            <X className="w-4 h-4 text-muted" />
          </button>
          
          <div className="flex items-start gap-4">
            <div className="p-2 rounded-lg bg-[#a855f7]/10">
              <Bot className="w-5 h-5 text-[#a855f7]" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-2">
                <h3 className="font-heading font-semibold text-base text-chalk truncate">
                  🤖 AI Detected: {selectedZone.label} Zone
                </h3>
              </div>
              <div className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
                <span className="text-muted">
                  Severity: <span className="font-mono text-chalk">{selectedZone.severity}</span>
                </span>
                <span className="text-muted">
                  Active Vehicles: <span className="font-mono text-chalk">{selectedZone.vehicle_count}</span>
                </span>
                <span className="text-muted">
                  Center: <span className="font-mono text-chalk">{selectedZone.center_lat.toFixed(4)}, {selectedZone.center_lon.toFixed(4)}</span>
                </span>
              </div>
              <button
                onClick={() => navigate('/dispatch')}
                className="mt-3 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#a855f7]/10 text-[#a855f7] text-sm font-medium hover:bg-[#a855f7]/20 transition-colors"
              >
                <Navigation className="w-3.5 h-3.5" />
                Dispatch Area Patrol
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function createCircleIcon(color, radius, isHollow = false) {
  const size = radius * 2 + 4
  const fill = isHollow ? 'transparent' : color
  return `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}"><circle cx="${size/2}" cy="${size/2}" r="${radius}" fill="${fill}" stroke="${color}" stroke-width="2" opacity="0.85"/></svg>`)}`
}

function createSpilloverIcon() {
  const size = 22
  const id = `glow-${Math.random().toString(36).slice(2, 8)}`
  return `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}">
    <defs>
      <filter id="${id}" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="2" result="blur"/>
        <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
    </defs>
    <circle cx="${size/2}" cy="${size/2}" r="8" fill="#a855f7" opacity="0.3" filter="url(#${id})"/>
    <circle cx="${size/2}" cy="${size/2}" r="5" fill="#a855f7" stroke="white" stroke-width="1.5"/>
    <circle cx="${size/2}" cy="${size/2}" r="2" fill="white"/>
  </svg>`)}`
}
