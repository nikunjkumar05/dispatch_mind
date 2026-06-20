import { useState, useEffect, useRef } from 'react'
import { mappls } from 'mappls-web-maps'
import { useApi, tierColor } from '../utils/api'
import { MapPin, Layers } from 'lucide-react'

const MAPPLS_KEY = import.meta.env.VITE_MAPPLS_API_KEY
const MAP_ID = 'dispatchmind-map'

export default function MapView() {
  const { data, loading } = useApi('/map-data')
  const [selectedViolation, setSelectedViolation] = useState(null)
  const [mapReady, setMapReady] = useState(false)
  const mapInstanceRef = useRef(null)
  const markersRef = useRef([])
  const mapplsRef = useRef(null)
  const initRef = useRef(false)

  useEffect(() => {
    if (initRef.current) return
    initRef.current = true

    const mapplsClass = new mappls()
    mapplsRef.current = mapplsClass

    mapplsClass.initialize(MAPPLS_KEY, { map: true, plugins: [] }, () => {
      try {
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
      }
    })

    return () => {
      markersRef.current.forEach(m => { try { m.remove() } catch(e) {} })
      markersRef.current = []
      if (mapInstanceRef.current) {
        try { mapInstanceRef.current.remove() } catch(e) {}
        mapInstanceRef.current = null
      }
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
        icon: createCircleIcon(tierColor(v.impact_tier), Math.max(4, Math.min(10, v.gridlock_score / 12))),
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
        icon: createCircleIcon('#B8960C', 12, true),
      })
      if (marker) markersRef.current.push(marker)
    })
  }, [mapReady, data])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[70vh]">
        <div className="text-mist/50 text-lg animate-pulse">Loading tactical map...</div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-heading font-bold text-2xl text-chalk flex items-center gap-2">
            <MapPin className="w-6 h-6 text-signal-emerald" />
            Tactical Map
          </h1>
          <p className="text-mist/50 text-sm mt-1">
            MapmyIndia satellite + violation overlay
          </p>
        </div>
        <div className="text-xs text-mist/40 flex items-center gap-1">
          <Layers className="w-3 h-3" />
          Powered by MapmyIndia
        </div>
      </div>

      <div className="relative">
        <div
          id={MAP_ID}
          className="w-full rounded-lg overflow-hidden border border-mist/10"
          style={{ height: '70vh', width: '100%' }}
        />

        <div className="absolute bottom-4 left-4 z-[1000] bg-asphalt/90 border border-mist/10 rounded-lg p-3">
          <p className="text-xs font-semibold text-mist/60 uppercase tracking-wider mb-2">Impact Tier</p>
          <div className="space-y-1">
            {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(tier => (
              <div key={tier} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: tierColor(tier) }} />
                <span className="text-xs text-mist/70">{tier}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="absolute bottom-4 right-4 z-[1000] bg-asphalt/90 border border-mist/10 rounded-lg p-3">
          <p className="text-xs font-semibold text-mist/60 uppercase tracking-wider mb-2">Markers</p>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-khaki" />
              <span className="text-xs text-mist/70">Junction (BTP)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-signal-red" />
              <span className="text-xs text-mist/70">High Impact</span>
            </div>
          </div>
        </div>
      </div>

      {selectedViolation && (
        <div className="card border-khaki/30">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="font-heading font-bold text-lg text-chalk">
                {selectedViolation.mapped_junction}
              </h3>
              <div className="flex flex-wrap gap-4 text-sm mt-2">
                <span className="text-mist/70">
                  Vehicle: <span className="font-mono text-chalk">{selectedViolation.vehicle_type}</span>
                </span>
                <span className="text-mist/70">
                  Delay: <span className="font-mono text-chalk">{selectedViolation.duration_minutes} min</span>
                </span>
                <span className="text-mist/70">
                  Impact: <span className="font-mono text-chalk">{selectedViolation.gridlock_score}</span>
                </span>
              </div>
              <p className="text-xs text-mist/40 mt-2">
                {selectedViolation.police_station} — {selectedViolation.single_violation}
              </p>
            </div>
            <span className={`tier-badge ${selectedViolation.impact_tier}`}>
              {selectedViolation.impact_tier}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

function createCircleIcon(color, radius, isHollow = false) {
  const size = radius * 2 + 4
  const fill = isHollow ? 'transparent' : color
  return `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}"><circle cx="${size/2}" cy="${size/2}" r="${radius}" fill="${fill}" stroke="${color}" stroke-width="2" opacity="0.8"/></svg>`)}`
}
