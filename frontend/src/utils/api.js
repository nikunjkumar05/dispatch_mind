import { useState, useEffect, useRef, useCallback } from 'react'

const API_BASE = '/api'
const CACHE_TTL = 5 * 60 * 1000 // 5 minutes

const cache = new Map()

function getCacheKey(endpoint) {
  return endpoint
}

function getCacheEntry(key) {
  const entry = cache.get(key)
  if (!entry) return null
  if (Date.now() - entry.ts > CACHE_TTL) {
    cache.delete(key)
    return null
  }
  return entry.data
}

function setCacheEntry(key, data) {
  cache.set(key, { data, ts: Date.now() })
}

export function useApi(endpoint, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const cacheKey = getCacheKey(endpoint)

  useEffect(() => {
    let cancelled = false

    const cached = getCacheEntry(cacheKey)
    if (cached) {
      setData(cached)
      setLoading(false)
      return () => { cancelled = true }
    }

    setLoading(true)
    setError(null)

    fetch(`${API_BASE}${endpoint}`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then(json => {
        if (!cancelled) {
          setCacheEntry(cacheKey, json)
          setData(json)
          setLoading(false)
        }
      })
      .catch(err => {
        if (!cancelled) {
          setError(err.message)
          setLoading(false)
        }
      })

    return () => { cancelled = true }
  }, deps)

  return { data, loading, error }
}

export function formatNumber(n) {
  if (n >= 100000) return (n / 100000).toFixed(1) + 'L'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return n.toString()
}

export function formatDelay(minutes) {
  if (minutes >= 1440) return (minutes / 1440).toFixed(1) + ' days'
  if (minutes >= 60) return (minutes / 60).toFixed(1) + ' hrs'
  return Math.round(minutes) + ' min'
}

export function tierColor(tier) {
  const colors = {
    CRITICAL: '#DC2626',
    HIGH: '#EA580C',
    MEDIUM: '#D97706',
    LOW: '#059669',
  }
  return colors[tier] || '#6B7280'
}
