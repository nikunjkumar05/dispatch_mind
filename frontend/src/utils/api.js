import { useState, useEffect } from "react";

export const API_BASE = import.meta.env.VITE_API_URL || "/api";
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes
const REQUEST_TIMEOUT_MS = 30000;
const RETRY_503_DELAY_MS = 3000;

const cache = new Map();

function getCacheKey(endpoint) {
  return endpoint;
}

function getCacheEntry(key) {
  const entry = cache.get(key);
  if (!entry) return null;
  if (Date.now() - entry.ts > CACHE_TTL) {
    cache.delete(key);
    return null;
  }
  return entry.data;
}

function setCacheEntry(key, data) {
  cache.set(key, { data, ts: Date.now() });
}

export function useApi(endpoint, deps = [], options = {}) {
  const { enabled = true } = options;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(Boolean(enabled && endpoint));
  const [error, setError] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const cacheKey = getCacheKey(endpoint);

  useEffect(() => {
    let cancelled = false;
    let retryTimer = null;

    if (!enabled || !endpoint) {
      setLoading(false);
      setError(null);
      if (!endpoint) setData(null);
      return () => {
        cancelled = true;
      };
    }

    const cached = getCacheEntry(cacheKey);
    if (cached && refreshKey === 0) {
      setData(cached);
      setLoading(false);
      return () => {
        cancelled = true;
      };
    }

    setLoading(true);
    setError(null);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    const token = localStorage.getItem("token");
    const headers = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    fetch(`${API_BASE}${endpoint}`, { 
      headers,
      signal: controller.signal 
    })
      .then((res) => {
        if (res.status === 401) {
          localStorage.removeItem("token");
          localStorage.removeItem("user");
          window.location.reload();
          throw new Error("Unauthorized");
        }
        if (res.status === 503) {
          const err = new Error("System initializing");
          err.status = 503;
          throw err;
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((json) => {
        if (cancelled) return;
        setCacheEntry(cacheKey, json);
        setData(json);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;

        if (err.status === 503) {
          setLoading(true);
          retryTimer = setTimeout(() => {
            if (!cancelled) setRefreshKey((k) => k + 1);
          }, RETRY_503_DELAY_MS);
          return;
        }

        setError(err.name === "AbortError" ? "Request timed out" : err.message);
        setLoading(false);
      })
      .finally(() => {
        clearTimeout(timeout);
      });

    return () => {
      cancelled = true;
      clearTimeout(timeout);
      if (retryTimer) clearTimeout(retryTimer);
      controller.abort();
    };
  }, [endpoint, enabled, refreshKey, cacheKey, ...deps]);

  const refetch = () => {
    if (cacheKey) cache.delete(cacheKey);
    setRefreshKey((k) => k + 1);
  };

  return { data, loading, error, refetch };
}

export function formatNumber(n) {
  if (n >= 100000) return (n / 100000).toFixed(1) + "L";
  if (n >= 1000) return (n / 1000).toFixed(1) + "K";
  return n.toString();
}

export function formatDelay(minutes) {
  if (minutes >= 1440) return (minutes / 1440).toFixed(1) + " days";
  if (minutes >= 60) return (minutes / 60).toFixed(1) + " hrs";
  return Math.round(minutes) + " min";
}

export function tierColor(tier) {
  const colors = {
    CRITICAL: "#FF3366",
    HIGH: "#FF6B35",
    MEDIUM: "#FFB800",
    LOW: "#00FF88",
  };
  return colors[tier] || "#6B7280";
}

export async function apiFetch(endpoint, options = {}) {
  const token = localStorage.getItem("token");
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  
  let cleanEndpoint = endpoint;
  if (endpoint.startsWith("/api/")) {
    cleanEndpoint = endpoint.substring(4);
  } else if (endpoint.startsWith("api/")) {
    cleanEndpoint = endpoint.substring(3);
  }
  
  const response = await fetch(`${API_BASE}${cleanEndpoint}`, {
    ...options,
    headers,
  });
  
  if (response.status === 401) {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    window.location.reload();
    throw new Error("Unauthorized");
  }
  
  return response;
}


