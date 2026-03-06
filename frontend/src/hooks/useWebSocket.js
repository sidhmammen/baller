import { useEffect, useRef, useCallback, useState } from 'react'

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

    // Use same host/port as the page — goes through Vite proxy
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const socket = new WebSocket(`ws://localhost:8000/notifications/ws/${sessionId}`)

    socket.onopen = () => {
      setConnected(true)
      console.log('[ws] Connected')
      socket._ping = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: 'ping' }))
        }
      }, 25000)
    }
    socket.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.type === 'today_games') { setTodayGames(data.games || []); return }
        if (data.type === 'pong') return
        onMessageRef.current?.(data)
      } catch {}
    }
    socket.onerror = (err) => console.error('[ws] Error', err)
    socket.onclose = () => {
      setConnected(false)
      clearInterval(socket._ping)
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