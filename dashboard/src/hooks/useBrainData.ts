'use client'

import { useState, useEffect, useCallback } from 'react'

interface WebSocketOptions {
  url: string
  onMessage?: (data: any) => void
  onError?: (error: Event) => void
  reconnectInterval?: number
  maxRetries?: number
}

interface WebSocketState {
  isConnected: boolean
  lastMessage: any
  error: Error | null
  send: (data: any) => void
  reconnect: () => void
}

export function useBrainWebSocket(options: WebSocketOptions): WebSocketState {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, _setLastMessage] = useState<any>(null)
  const [error, setError] = useState<Error | null>(null)
  const [ws, _setWs] = useState<WebSocket | null>(null)
  const [retryCount, setRetryCount] = useState(0)

  const {
    url,
    onMessage: _onMessage,
    onError: _onError,
    reconnectInterval = 5000,
    maxRetries = 5,
  } = options

  const connect = useCallback(() => {
    try {
      // For now, use polling as WebSocket server not yet available
      // TODO: Implement actual WebSocket when BRAIN supports it
      console.log('WebSocket: Using polling fallback for', url)
      setIsConnected(true)
    } catch (err) {
      setError(err as Error)
      setIsConnected(false)
    }
  }, [url])

  const send = useCallback((data: any) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data))
    }
  }, [ws])

  const reconnect = useCallback(() => {
    if (retryCount < maxRetries) {
      setRetryCount(prev => prev + 1)
      setTimeout(connect, reconnectInterval)
    }
  }, [connect, reconnectInterval, maxRetries, retryCount])

  useEffect(() => {
    connect()
    return () => {
      if (ws) {
        ws.close()
      }
    }
  }, [connect])

  return { isConnected, lastMessage, error, send, reconnect }
}

// Polling hook for real-time data (fallback until WebSocket ready)
export function useBrainPolling<T>(
  fetchFn: () => Promise<T>,
  intervalMs: number = 5000
): { data: T | null; loading: boolean; error: Error | null; refresh: () => void } {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const refresh = useCallback(async () => {
    try {
      setLoading(true)
      const result = await fetchFn()
      setData(result)
      setError(null)
    } catch (err) {
      setError(err as Error)
    } finally {
      setLoading(false)
    }
  }, [fetchFn])

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, intervalMs)
    return () => clearInterval(interval)
  }, [refresh, intervalMs])

  return { data, loading, error, refresh }
}
