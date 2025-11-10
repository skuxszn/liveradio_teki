import { useEffect, useRef } from 'react'
import { useWsStore } from '@/store/wsStore'
import { useQueryClient } from '@tanstack/react-query'

export function useWebsocketEvents() {
  const setConnected = useWsStore((s) => s.setConnected)
  const setEvent = useWsStore((s) => s.setEvent)
  const bumpReconnect = useWsStore((s) => s.bumpReconnect)
  const wsRef = useRef<WebSocket | null>(null)
  const queryClient = useQueryClient()

  const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const inferredBackend = `${scheme}://${window.location.hostname}:9001/ws`
  const configured = (import.meta as any).env?.VITE_API_WS_URL as string | undefined
  const url = (configured || inferredBackend)

  useEffect(() => {
    let retryMs = 1000
    let closed = false

    const connect = () => {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        retryMs = 1000
      }

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data)
          setEvent(msg.type, msg.data)
          // Invalidate relevant queries based on event types
          if (msg.type === 'stream_status_changed' || msg.type === 'track_changed') {
            queryClient.invalidateQueries({ queryKey: ['stream-status'] })
          } else if (msg.type === 'metric_update') {
            queryClient.invalidateQueries({ queryKey: ['metrics-current'] })
          } else if (msg.type === 'mappings_updated') {
            queryClient.invalidateQueries({ queryKey: ['mappings'] })
            queryClient.invalidateQueries({ queryKey: ['mapping-stats'] })
          } else if (msg.type === 'assets_updated') {
            queryClient.invalidateQueries({ queryKey: ['assets'] })
            queryClient.invalidateQueries({ queryKey: ['asset-stats'] })
          }
        } catch {
          // ignore
        }
      }

      ws.onclose = () => {
        setConnected(false)
        if (closed) return
        bumpReconnect()
        setTimeout(connect, retryMs)
        retryMs = Math.min(retryMs * 2, 15000)
      }
      ws.onerror = () => ws.close()
    }

    connect()
    return () => {
      closed = true
      wsRef.current?.close()
    }
  }, [url, setConnected, setEvent, bumpReconnect])
}


