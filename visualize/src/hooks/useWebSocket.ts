import { useEffect, useRef, useState, useCallback } from 'react'
import { useStore } from '../store'
import type { WSMessage } from '../types'

export function useWebSocket() {
  const [connected, setConnected] = useState(false)
  const [reconnecting, setReconnecting] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const pingIntervalRef = useRef<ReturnType<typeof setInterval>>()
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>()
  // FIX: Track unmount to prevent WebSocket reconnection after component teardown.
  // Without this, ws.onclose fires during cleanup → scheduleReconnect → new socket after unmount.
  const disposedRef = useRef(false)
  // FIX: Use a ref to break the circular dependency between connect and scheduleReconnect.
  // connect → ws.onclose → scheduleReconnect → setTimeout(connect). Without a ref,
  // this creates a stale closure or a dependency cycle in useCallback.
  const connectRef = useRef<() => void>()
  // FIX: Individual selectors prevent re-renders on unrelated state changes
  const setArchive = useStore(s => s.setArchive)
  const setWsConnected = useStore(s => s.setWsConnected)
  const setLive = useStore(s => s.setLive)

  const getWsUrl = useCallback(() => {
    if (import.meta.env.DEV) return 'ws://localhost:3141/ws'
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${proto}//${window.location.host}/ws`
  }, [])

  const connect = useCallback(() => {
    // FIX: Guard against both OPEN and CONNECTING states to prevent duplicate
    // WebSocket connections during React 18 StrictMode double-mount.
    const rs = wsRef.current?.readyState
    if (rs === WebSocket.OPEN || rs === WebSocket.CONNECTING) return

    try {
      const ws = new WebSocket(getWsUrl())
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        setReconnecting(false)
        setWsConnected(true)
        setLive(true)
        reconnectAttempts.current = 0

        // Heartbeat
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }))
          }
        }, 30000)
      }

      ws.onmessage = (event) => {
        try {
          const msg: WSMessage = JSON.parse(event.data)
          const store = useStore.getState()

          switch (msg.type) {
            case 'archive':
              store.setArchive(msg.data)
              break
            case 'session_update': {
              const archive = store.archive
              if (!archive) break
              const idx = archive.sessions.findIndex(s => s.session_id === msg.data.session_id)
              const sessions = [...archive.sessions]
              if (idx >= 0) {
                sessions[idx] = msg.data
              } else {
                sessions.push(msg.data)
              }
              store.setArchive({ ...archive, sessions })
              break
            }
            case 'new_event': {
              const archive = store.archive
              if (!archive) break
              const sessions = archive.sessions.map(s => {
                if (s.session_id === msg.data.session_id) {
                  const existingIdx = s.nodes.findIndex(n => n.node_id === msg.data.node_id)
                  const nodes = [...s.nodes]
                  if (existingIdx >= 0) {
                    nodes[existingIdx] = msg.data
                  } else {
                    nodes.push(msg.data)
                  }
                  return { ...s, nodes, isActive: true, lastEventAt: msg.data.timestamp }
                }
                return s
              })
              store.setArchive({ ...archive, sessions })
              break
            }
            case 'pong':
              break
          }
        } catch {
          // Ignore malformed messages
        }
      }

      ws.onclose = () => {
        setConnected(false)
        setWsConnected(false)
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current)
        // Only reconnect if we haven't been disposed (unmounted).
        // Use connectRef to break the circular dependency (connect ↔ scheduleReconnect).
        if (!disposedRef.current) {
          setReconnecting(true)
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000)
          reconnectAttempts.current++
          reconnectTimeoutRef.current = setTimeout(() => connectRef.current?.(), delay)
        }
      }

      ws.onerror = () => {
        ws.close()
      }
    } catch {
      // Connection failed — schedule reconnect via ref
      if (!disposedRef.current) {
        setReconnecting(true)
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000)
        reconnectAttempts.current++
        reconnectTimeoutRef.current = setTimeout(() => connectRef.current?.(), delay)
      }
    }
  }, [getWsUrl, setWsConnected, setLive])

  // Keep ref current so reconnection always calls the latest version of connect
  connectRef.current = connect

  useEffect(() => {
    disposedRef.current = false
    connect()
    return () => {
      disposedRef.current = true
      if (wsRef.current) wsRef.current.close()
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current)
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current)
    }
  }, [connect])

  return { connected, reconnecting }
}
