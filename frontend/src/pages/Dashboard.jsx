import { useState, useCallback, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getNotifications } from '../lib/api'
import { useWebSocket } from '../hooks/useWebSocket'
import { WeeklySchedule } from '../components/WeeklySchedule'
import { WaiverTargets } from '../components/WaiverTargets'
import { GamesTicker } from '../components/GamesTicker'
import { clsx } from 'clsx'

export function Dashboard({ sessionId, onResetRoster, activeTab, onTabChange, onConnectedChange }) {
  const [liveAlert, setLiveAlert] = useState(null)
  const qc = useQueryClient()

  const notifQuery = useQuery({
    queryKey: ['notifications', sessionId],
    queryFn: () => getNotifications(sessionId).then(r => r.data),
    enabled: !!sessionId,
    staleTime: 30000,
  })

  const handleWsMessage = useCallback((msg) => {
    if (msg.type === 'lineup_alert') {
      setLiveAlert(msg)
      // Add to top of notifications
      qc.setQueryData(['notifications', sessionId], (old) => {
        const newNotif = {
          id: Date.now(),
          player_id: msg.player_id,
          player_name: msg.player_name,
          notification_type: msg.notification_type,
          message: msg.message,
          is_read: false,
          created_at: new Date().toISOString(),
        }
        return [newNotif, ...(old || [])]
      })
      // Clear live banner after 8 seconds
      setTimeout(() => setLiveAlert(null), 8000)
    }
  }, [sessionId, qc])

  const { connected, todayGames } = useWebSocket(sessionId, handleWsMessage)

  // Update parent with connection status
  useEffect(() => {
    onConnectedChange?.(connected)
  }, [connected, onConnectedChange])

  return (
    <div className="min-h-screen">
      {/* Live alert banner */}
      {liveAlert && (
        <div className={clsx(
          'sticky top-0 z-30 px-4 py-2 slide-in text-sm font-medium flex items-center justify-center gap-2 mb-4',
          liveAlert.is_starter
            ? 'bg-green-500 text-white'
            : 'bg-red-500 text-white'
        )}>
          {liveAlert.message}
        </div>
      )}

      {/* Games ticker */}
      {todayGames.length > 0 && (
        <div className="border-b border-white/5 bg-zinc-950/50 rounded-xl mb-6">
          <div className="px-2 py-2">
            <GamesTicker games={todayGames} />
          </div>
        </div>
      )}

      {/* Content - based on activeTab from sidebar */}
      <div className="space-y-4">
        {activeTab === 'roster' && <WeeklySchedule sessionId={sessionId} />}
        {activeTab === 'waiver' && <WaiverTargets sessionId={sessionId} />}
      </div>
    </div>
  )
}