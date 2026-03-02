import { useEffect, useRef, useCallback, useState } from 'react'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

export function useWebSocket(sessionId, onMessage) {
  const ws = useRef(null)
  const [connected, setConnected] = useState(false)
  const [todayGames, setTodayGames] = useState([])
  const reconnectTimeout = useRef(null)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  const connect = useCallback(() => {
    if (!sessionId) return
    if (ws.current?.readyState === WebSocket.OPEN) return

    const url = `${WS_URL}/notifications/ws/${sessionId}`
    const socket = new WebSocket(url)

    socket.onopen = () => {
      setConnected(true)
      console.log('[ws] Connected')
      // Start ping interval
      socket._pingInterval = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: 'ping' }))
        }
      }, 25000)
    }

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'today_games') {
          setTodayGames(data.games || [])
          return
        }
        if (data.type === 'pong') return
        onMessageRef.current?.(data)
      } catch (e) {
        console.error('[ws] Parse error', e)
      }
    }

    socket.onerror = (err) => {
      console.error('[ws] Error', err)
    }

    socket.onclose = () => {
      setConnected(false)
      clearInterval(socket._pingInterval)
      console.log('[ws] Disconnected — reconnecting in 3s...')
      reconnectTimeout.current = setTimeout(connect, 3000)
    }

    ws.current = socket
  }, [sessionId])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimeout.current)
      ws.current?.close()
    }
  }, [connect])

  return { connected, todayGames }
}
