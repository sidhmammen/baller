import { useState, useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getNotifications } from '../lib/api'
import { useWebSocket } from '../hooks/useWebSocket'
import { WeeklySchedule } from '../components/WeeklySchedule'
import { WaiverTargets } from '../components/WaiverTargets'
import { NotificationBell } from '../components/NotificationBell'
import { GamesTicker } from '../components/GamesTicker'
import { Settings, RefreshCw } from 'lucide-react'
import { clsx } from 'clsx'

const TABS = [
  { id: 'schedule', label: 'MY ROSTER' },
  { id: 'waiver', label: 'WAIVER WIRE' },
]

export function Dashboard({ sessionId, onResetRoster }) {
  const [activeTab, setActiveTab] = useState('schedule')
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

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-court-950/90 backdrop-blur-md border-b border-court-800">
        <div className="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="font-display text-2xl text-white tracking-widest">baller</h1>
            <div className={clsx(
              'flex items-center gap-1.5 text-[10px] font-mono px-2 py-0.5 rounded-full border',
              connected
                ? 'text-green-400 border-green-500/30 bg-green-500/10'
                : 'text-slate-500 border-slate-700 bg-transparent'
            )}>
              <span className={clsx(
                'w-1.5 h-1.5 rounded-full',
                connected ? 'bg-green-400 animate-pulse' : 'bg-slate-500'
              )} />
              {connected ? 'LIVE' : 'offline'}
            </div>
          </div>

          <div className="flex items-center gap-1">
            <NotificationBell
              sessionId={sessionId}
              notifications={notifQuery.data || []}
              onMarkRead={() => qc.invalidateQueries(['notifications', sessionId])}
            />
            <button
              onClick={() => {
                qc.invalidateQueries(['schedule', sessionId])
                qc.invalidateQueries(['waiver', sessionId])
              }}
              className="p-2 rounded-lg text-slate-400 hover:text-brand hover:bg-court-800 transition-colors"
              title="Refresh"
            >
              <RefreshCw size={16} />
            </button>
            <button
              onClick={onResetRoster}
              className="p-2 rounded-lg text-slate-400 hover:text-brand hover:bg-court-800 transition-colors"
              title="Change roster"
            >
              <Settings size={16} />
            </button>
          </div>
        </div>
      </header>

      {/* Live alert banner */}
      {liveAlert && (
        <div className={clsx(
          'sticky top-14 z-30 px-4 py-2 slide-in text-sm font-medium flex items-center justify-center gap-2',
          liveAlert.is_starter
            ? 'bg-green-500 text-white'
            : 'bg-red-500 text-white'
        )}>
          {liveAlert.message}
        </div>
      )}

      {/* Games ticker */}
      {todayGames.length > 0 && (
        <div className="border-b border-court-800 bg-court-950/50">
          <div className="max-w-4xl mx-auto px-4 py-2">
            <GamesTicker games={todayGames} />
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-court-800">
        <div className="max-w-4xl mx-auto px-4 flex gap-6">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                'py-3 text-sm font-display tracking-wider border-b-2 transition-colors',
                activeTab === tab.id
                  ? 'border-brand text-brand'
                  : 'border-transparent text-slate-500 hover:text-slate-300',
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 py-6">
        {activeTab === 'schedule' && <WeeklySchedule sessionId={sessionId} />}
        {activeTab === 'waiver' && <WaiverTargets sessionId={sessionId} />}
      </main>
    </div>
  )
}
