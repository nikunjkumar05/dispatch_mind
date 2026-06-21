import { useState, useEffect } from 'react'

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

export function useApi(endpoint, deps = [], options = {}) {
  const { enabled = true } = options
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(enabled)
  const [error, setError] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const cacheKey = getCacheKey(endpoint)

  useEffect(() => {
    let cancelled = false

    if (!enabled) {
      setLoading(false)
      setError(null)
      return () => { cancelled = true }
    }

    const cached = getCacheEntry(cacheKey)
    if (cached && refreshKey === 0) {
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
  }, [...deps, refreshKey, enabled])

  const refetch = () => {
    cache.delete(cacheKey)
    setRefreshKey(k => k + 1)
  }

  return { data, loading, error, refetch }
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
    CRITICAL: '#EF4444',
    HIGH: '#F97316',
    MEDIUM: '#EAB308',
    LOW: '#22C55E',
  }
  return colors[tier] || '#6B7280'
}

export function tierGlow(tier) {
  const glows = {
    CRITICAL: '0 0 20px rgba(239, 68, 68, 0.15)',
    HIGH: '0 0 20px rgba(249, 115, 22, 0.15)',
    MEDIUM: '0 0 20px rgba(234, 179, 8, 0.15)',
    LOW: '0 0 20px rgba(34, 197, 94, 0.15)',
  }
  return glows[tier] || 'none'
}
