import { useState, useEffect, useRef } from 'react'
import { Bell, X, CheckCheck, AlertTriangle, CheckCircle } from 'lucide-react'
import { markAllRead } from '../lib/api'
import { clsx } from 'clsx'

export function NotificationBell({ sessionId, notifications, onMarkRead }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const unread = notifications.filter(n => !n.is_read).length

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleMarkAll = async () => {
    if (!sessionId) return
    await markAllRead(sessionId)
    onMarkRead?.()
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(o => !o)}
        className="relative p-2 rounded-lg text-slate-400 hover:text-brand hover:bg-court-800 transition-colors"
      >
        <Bell size={20} />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center bg-red-500 text-white text-[10px] font-bold rounded-full px-1 pulse-glow">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-96 card shadow-2xl shadow-black/50 z-50 slide-in">
          <div className="flex items-center justify-between p-4 border-b border-court-700">
            <span className="font-display text-lg text-white tracking-wide">ALERTS</span>
            <div className="flex items-center gap-2">
              {unread > 0 && (
                <button onClick={handleMarkAll} className="text-xs text-slate-400 hover:text-brand flex items-center gap-1">
                  <CheckCheck size={13} /> Mark all read
                </button>
              )}
              <button onClick={() => setOpen(false)} className="text-slate-500 hover:text-white">
                <X size={16} />
              </button>
            </div>
          </div>
          <div className="max-h-96 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-sm">
                No alerts yet. Lineup notifications will appear here before games.
              </div>
            ) : (
              notifications.map(n => (
                <NotificationItem key={n.id} notification={n} />
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function NotificationItem({ notification }) {
  const isStart = notification.notification_type === 'starting'
  return (
    <div className={clsx(
      'flex items-start gap-3 p-4 border-b border-court-800 last:border-0',
      !notification.is_read && 'bg-court-800/50',
    )}>
      <div className={clsx('mt-0.5 flex-shrink-0', isStart ? 'text-green-400' : 'text-red-400')}>
        {isStart ? <CheckCircle size={16} /> : <AlertTriangle size={16} />}
      </div>
      <div className="flex-1 min-w-0">
        <p className={clsx('text-sm font-medium', isStart ? 'text-green-300' : 'text-red-300')}>
          {notification.player_name}
        </p>
        <p className="text-xs text-slate-400 mt-0.5">{notification.message}</p>
        <p className="text-[10px] text-slate-600 mt-1">
          {notification.created_at ? new Date(notification.created_at).toLocaleTimeString() : ''}
        </p>
      </div>
      {!notification.is_read && (
        <div className="w-2 h-2 rounded-full bg-brand flex-shrink-0 mt-1.5" />
      )}
    </div>
  )
}

export function NotificationFeed({ notifications, liveAlert }) {
  return (
    <div className="space-y-2">
      {liveAlert && (
        <div className={clsx(
          'flex items-center gap-3 p-3 rounded-lg border slide-in',
          liveAlert.is_starter
            ? 'bg-green-500/10 border-green-500/30'
            : 'bg-red-500/10 border-red-500/30'
        )}>
          {liveAlert.is_starter ? (
            <CheckCircle size={16} className="text-green-400 flex-shrink-0" />
          ) : (
            <AlertTriangle size={16} className="text-red-400 flex-shrink-0" />
          )}
          <span className="text-sm font-medium text-white">{liveAlert.message}</span>
        </div>
      )}
      {notifications.slice(0, 5).map(n => (
        <NotificationItem key={n.id} notification={n} />
      ))}
    </div>
  )
}
