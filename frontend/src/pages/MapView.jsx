import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useApi, tierColor } from "../utils/api";
import {
  MapPin,
  Layers,
  X,
  AlertTriangle,
  Bot,
  Navigation,
} from "lucide-react";
import ErrorState from "../components/ErrorState";
import TierBadge from "../components/TierBadge";
import ScrollReveal from "../components/ScrollReveal";
import PageHeader from "../components/PageHeader";

const BENGALURU_CENTER = [12.9716, 77.5946];

const TIER_RADIUS = {
  CRITICAL: 12,
  HIGH: 10,
  MEDIUM: 8,
  LOW: 6,
};

function createCircleIcon(color, size = 12) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}"><circle cx="${size/2}" cy="${size/2}" r="${size/2 - 1}" fill="${color}" stroke="#fff" stroke-width="1.5"/></svg>`;
  return "data:image/svg+xml," + encodeURIComponent(svg);
}

function createRingIcon(color = "#3B82F6", size = 20) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}"><circle cx="${size/2}" cy="${size/2}" r="${size/2 - 2}" fill="transparent" stroke="${color}" stroke-width="2"/></svg>`;
  return "data:image/svg+xml," + encodeURIComponent(svg);
}

export default function MapView() {
  const navigate = useNavigate();
  const { data, loading, error, refetch } = useApi("/map-data");
  const [showSpillover, setShowSpillover] = useState(false);
  const { data: spilloverData, loading: spilloverLoading } = useApi(
    "/spillover-zones",
    [],
    { enabled: showSpillover },
  );
  const [selectedViolation, setSelectedViolation] = useState(null);
  const [selectedZone, setSelectedZone] = useState(null);
  const [flyTarget, setFlyTarget] = useState(null);
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState(null);

  const mapRef = useRef(null);
  const layersRef = useRef({ markers: [], circles: [], infoWindows: [] });
  const initRef = useRef(false);

  const clearLayers = useCallback(() => {
    if (!mapRef.current || !window.mappls) return;
    try {
      layersRef.current.markers.forEach((m) => {
        window.mappls.removeLayer({ map: mapRef.current, layer: m });
      });
      layersRef.current.circles.forEach((c) => {
        window.mappls.removeLayer({ map: mapRef.current, layer: c });
      });
    } catch (e) {
      console.warn("Error clearing layers", e);
    }
    layersRef.current = { markers: [], circles: [], infoWindows: [] };
  }, []);

  const renderLayers = useCallback(() => {
    if (!mapRef.current || !data || !window.mappls) return;
    clearLayers();

    const violations = data?.violations || [];
    const junctions = data?.junctions || [];

    try {
      violations.forEach((v) => {
        const color = tierColor(v.impact_tier);
        const icon = createCircleIcon(color, TIER_RADIUS[v.impact_tier] || 8);
        const marker = new window.mappls.Marker({
          map: mapRef.current,
          position: { lat: v.latitude, lng: v.longitude },
          icon,
          width: TIER_RADIUS[v.impact_tier] || 8,
          height: TIER_RADIUS[v.impact_tier] || 8,
          offset: [0, 0],
          popupHtml: `
            <div style="font-family: Inter, sans-serif; padding: 4px; min-width: 160px;">
              <strong>${v.mapped_junction || "Violation"}</strong><br/>
              <span style="color:#666; font-size:12px;">
                Vehicle: ${v.vehicle_type}<br/>
                Delay: ${v.duration_minutes} min<br/>
                Score: ${v.gridlock_score}
              </span>
            </div>
          `,
          popupOptions: { openPopup: false, autoClose: true, maxWidth: 280 },
        });
        marker.addListener("click", () => {
          setSelectedViolation(v);
          setSelectedZone(null);
          setFlyTarget([v.latitude, v.longitude]);
        });
        layersRef.current.markers.push(marker);
      });

      junctions.forEach((j) => {
        const icon = createRingIcon("#3B82F6", 22);
        const marker = new window.mappls.Marker({
          map: mapRef.current,
          position: { lat: j.lat, lng: j.lon },
          icon,
          width: 22,
          height: 22,
          offset: [0, 0],
        });
        marker.addListener("click", () => {
          setFlyTarget([j.lat, j.lon]);
          setSelectedViolation(null);
        });
        layersRef.current.markers.push(marker);
      });

      if (showSpillover && spilloverData?.zones) {
        spilloverData.zones.forEach((zone) => {
          const circle = new window.mappls.Circle({
            map: mapRef.current,
            center: { lat: String(zone.center_lat), lng: String(zone.center_lon) },
            radius: 200,
            strokeColor: "#a855f7",
            strokeOpacity: 0.8,
            strokeWeight: 2,
            fillColor: "#a855f7",
            fillOpacity: 0.2,
          });
          circle.addListener("click", () => {
            setSelectedZone(zone);
            setSelectedViolation(null);
            setFlyTarget([zone.center_lat, zone.center_lon]);
          });
          layersRef.current.circles.push(circle);
        });
      }
    } catch (e) {
      console.warn("Error rendering layers", e);
    }
  }, [data, showSpillover, spilloverData, clearLayers]);

  useEffect(() => {
    let active = true;

    async function loadMappls() {
      // Hardcoded fallback key as requested by user
      let apiKey = import.meta.env.VITE_MAPPLS_API_KEY || "ldvrbvdbrzthemtasdlbdfddbcgnmfpnklz";
      
      // If build-time variable is absent and hardcoded key is not used, fetch from backend config API
      if (!apiKey) {
        try {
          const res = await fetch("/api/config/mappls");
          if (res.ok) {
            const config = await res.json();
            apiKey = config.apiKey;
          }
        } catch (e) {
          console.warn("Failed to fetch Mappls config from backend", e);
        }
      }

      if (!active) return;

      if (!apiKey) {
        setMapError("Mappls API key is missing. Check your server environment variables.");
        return;
      }

      if (initRef.current) return;
      initRef.current = true;

      // Load map on script load instead of global callback
      const initMap = () => {
        try {
          if (!window.mappls) {
            setMapError("Map SDK failed to load completely.");
            return;
          }

          const mapInstance = new window.mappls.Map('map', {
            center: BENGALURU_CENTER,
            zoom: 12,
            zoomControl: true,
          });

          if (!mapInstance) {
            setMapError("Failed to create map instance.");
            return;
          }

          mapRef.current = mapInstance;
          mapInstance.addListener("load", () => {
            setMapReady(true);
            setMapError(null);
          });
        } catch (err) {
          console.error("Mappls init error:", err);
          setMapError("Failed to initialize map tiles.");
        }
      };

      // Prevent adding multiple scripts if strict mode runs twice
      let script = document.getElementById("mappls-sdk-script");
      if (!script) {
        script = document.createElement("script");
        script.id = "mappls-sdk-script";
        script.src = `https://sdk.mappls.com/map/sdk/web?v=3.0&access_token=${apiKey}`;
        script.async = true;
        script.defer = true;
        script.onload = initMap;
        script.onerror = () => setMapError("Network error loading Mappls SDK. Is your API key valid?");
        document.head.appendChild(script);
      } else {
        // If script is already there and loaded, we can just call our init manually
        if (window.mappls && !mapRef.current) {
          initMap();
        }
      }
    }

    loadMappls();

    return () => {
      active = false;
      // We do not remove the script on unmount to save bandwidth,
      // but we do want to clean up the map instance.
      if (mapRef.current && window.mappls) {
        try {
           const mapEl = document.getElementById("map");
           if (mapEl) mapEl.innerHTML = "";
        } catch (e) {}
        mapRef.current = null;
      }
      initRef.current = false;
      setMapReady(false);
    };
  }, []);

  useEffect(() => {
    if (!mapReady || !mapRef.current || !window.mappls) return;

    if (flyTarget) {
      try {
        mapRef.current.flyTo({ center: flyTarget, zoom: 15 });
      } catch (e) {
        console.warn("FlyTo failed", e);
      }
    }

    renderLayers();
  }, [mapReady, flyTarget, renderLayers]);

  const violations = data?.violations || [];
  const junctions = data?.junctions || [];
  const showLoadingOverlay = (loading || !mapReady) && !mapError && !error;
  const showApiError = error && mapReady;
  const showApiErrorOverlay = error && !mapReady && !mapError && !loading;

  return (
    <div className="space-y-4">
      <ScrollReveal>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <PageHeader
            icon={MapPin}
            iconColor="text-signal-emerald"
            title="Tactical Map"
            subtitle="Violation hotspots across Bengaluru"
          />
          <div className="text-xs text-muted flex items-center gap-1">
            <Layers className="w-3 h-3" />
            Mappls
          </div>
        </div>
      </ScrollReveal>

      <ScrollReveal delay={50}>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setShowSpillover((v) => !v)}
            className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm transition-all ${
              showSpillover
                ? "bg-[#a855f7]/10 border-[#a855f7]/30 text-[#c084fc]"
                : "bg-surface/50 border-border text-muted hover:text-chalk hover:border-neon-blue/30"
            }`}
          >
            <Bot className="w-3.5 h-3.5" />
            {spilloverLoading
              ? "Loading spillover..."
              : showSpillover
                ? "Hide Spillover Zones"
                : "Show Spillover Zones"}
          </button>
        </div>
      </ScrollReveal>

      <div className="relative rounded-xl border border-border" style={{ height: "70vh" }}>
        <div
          id="map"
          style={{ width: "100%", height: "100%" }}
        />

        {/* Loading overlay */}
        {showLoadingOverlay && (
          <div className="absolute inset-0 flex items-center justify-center bg-base/80 z-[1001]">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-2 border-neon-blue/30 border-t-neon-blue rounded-full animate-spin" />
              <p className="text-muted text-sm font-medium">
                {loading ? "Connecting to server..." : "Loading tactical map..."}
              </p>
            </div>
          </div>
        )}

        {/* API error overlay (before map is ready) */}
        {showApiErrorOverlay && (
          <div className="absolute inset-0 flex items-center justify-center bg-base/80 z-[1001]">
            <ErrorState message={error} onRetry={refetch} />
          </div>
        )}

        {/* Map error overlay */}
        {mapError && (
          <div className="absolute inset-0 flex items-center justify-center bg-base/80 z-[1001]">
            <div className="glass-card-static p-6 max-w-md text-center">
              <p className="text-signal-red font-medium mb-2">Map Error</p>
              <p className="text-muted text-sm mb-4">{mapError}</p>
              <button
                onClick={() => window.location.reload()}
                className="bg-neon-blue text-white px-4 py-2 rounded font-medium text-sm"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {/* API error overlay */}
        {showApiError && (
          <div className="absolute inset-0 flex items-center justify-center bg-base/80 z-[1001]">
            <ErrorState message={error} onRetry={refetch} />
          </div>
        )}

        {/* Legend */}
        {mapReady && (
          <>
            <div className="absolute bottom-4 left-4 z-[1000] glass-card-static p-3">
              <p className="text-[10px] font-semibold text-muted uppercase tracking-wider mb-2">
                Impact Tier
              </p>
              <div className="space-y-1.5">
                {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((tier) => (
                  <div key={tier} className="flex items-center gap-2">
                    <div
                      className="w-2.5 h-2.5 rounded-full"
                      style={{ backgroundColor: tierColor(tier) }}
                    />
                    <span className="text-xs text-muted">{tier}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="absolute bottom-4 right-4 z-[1000] glass-card-static p-3">
              <p className="text-[10px] font-semibold text-muted uppercase tracking-wider mb-2">
                Markers
              </p>
              <div className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full border-2 border-neon-blue bg-transparent" />
                  <span className="text-xs text-muted">Junction (BTP)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-signal-red" />
                  <span className="text-xs text-muted">Violation</span>
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full border-2 border-dashed"
                    style={{
                      borderColor: "#a855f7",
                      backgroundColor: "rgba(168,85,247,0.3)",
                    }}
                  />
                  <span className="text-xs text-muted">AI Spillover Zone</span>
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Selected Violation Detail */}
      {selectedViolation && (
        <ScrollReveal delay={50}>
          <div className="glass-card border-neon-blue/20 relative">
            <button
              onClick={() => setSelectedViolation(null)}
              className="absolute top-3 right-3 p-1 rounded-lg hover:bg-elevated border border-transparent hover:border-border transition-colors"
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
                    Vehicle:{" "}
                    <span className="font-mono text-chalk">
                      {selectedViolation.vehicle_type}
                    </span>
                  </span>
                  <span className="text-muted">
                    Delay:{" "}
                    <span className="font-mono text-chalk">
                      {selectedViolation.duration_minutes} min
                    </span>
                  </span>
                  <span className="text-muted">
                    Score:{" "}
                    <span className="font-mono text-chalk">
                      {selectedViolation.gridlock_score}
                    </span>
                  </span>
                </div>
                <p className="text-xs text-muted mt-2">
                  {selectedViolation.police_station} —{" "}
                  {selectedViolation.single_violation}
                </p>
              </div>
            </div>
          </div>
        </ScrollReveal>
      )}

      {/* Selected Spillover Zone Detail */}
      {selectedZone && (
        <ScrollReveal delay={50}>
          <div
            className="glass-card border-[#a855f7]/20 relative"
            style={{ boxShadow: "0 0 20px rgba(168,85,247,0.1)" }}
          >
            <button
              onClick={() => setSelectedZone(null)}
              className="absolute top-3 right-3 p-1 rounded-lg hover:bg-elevated border border-transparent hover:border-border transition-colors"
            >
              <X className="w-4 h-4 text-muted" />
            </button>

            <div className="flex items-start gap-4">
              <div className="p-2 rounded-lg bg-[#a855f7]/10">
                <Bot className="w-5 h-5 text-[#a855f7]" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-heading font-semibold text-base text-chalk truncate mb-2">
                  AI Detected: {selectedZone.label} Zone
                </h3>
                <div className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
                  <span className="text-muted">
                    Severity:{" "}
                    <span className="font-mono text-chalk">
                      {selectedZone.severity}
                    </span>
                  </span>
                  <span className="text-muted">
                    Active Vehicles:{" "}
                    <span className="font-mono text-chalk">
                      {selectedZone.vehicle_count}
                    </span>
                  </span>
                  <span className="text-muted">
                    Center:{" "}
                    <span className="font-mono text-chalk">
                      {selectedZone.center_lat.toFixed(4)},{" "}
                      {selectedZone.center_lon.toFixed(4)}
                    </span>
                  </span>
                </div>
                <button
                  onClick={() => navigate("/dispatch")}
                  className="mt-3 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#a855f7]/10 text-[#a855f7] text-sm font-medium hover:bg-[#a855f7]/20 transition-colors"
                >
                  <Navigation className="w-3.5 h-3.5" />
                  Dispatch Area Patrol
                </button>
              </div>
            </div>
          </div>
        </ScrollReveal>
      )}
    </div>
  );
}
