import { useQuery } from '@tanstack/react-query'
import { getWeeklySchedule } from '../lib/api'
import { ScoreRing, RecommendationBadge, WeekCalendar } from './ScoreComponents'
import { clsx } from 'clsx'
import { Info, Zap, Calendar } from 'lucide-react'
import { useState } from 'react'

export function WeeklySchedule({ sessionId }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['schedule', sessionId],
    queryFn: () => getWeeklySchedule(sessionId).then(r => r.data),
    enabled: !!sessionId,
    staleTime: 60000,
    refetchInterval: 300000, // refetch every 5 min
  })

  if (isLoading) return <ScheduleSkeleton />
  if (error) return (
    <div className="card p-8 text-center text-slate-500">
      Error loading schedule. Backend may be warming up.
    </div>
  )

  const players = data?.players || []

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="font-display text-2xl text-white tracking-wider">THIS WEEK</h2>
          <p className="text-xs text-slate-500 mt-0.5">Stream scores for your roster</p>
        </div>
        <FormulaTooltip />
      </div>

      {players.length === 0 ? (
        <div className="card p-10 text-center text-slate-500">
          No players on your roster yet.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {players.map((p, i) => (
            <PlayerWeekCard key={p.player_id} player={p} index={i} />
          ))}
        </div>
      )}
    </div>
  )
}

function PlayerWeekCard({ player, index }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      className={clsx('card-hover p-4 cursor-pointer fade-up', `stagger-${Math.min(index + 1, 5)}`)}
      onClick={() => setExpanded(e => !e)}
    >
      <div className="flex items-center gap-4">
        {/* Headshot */}
        <div className="w-12 h-12 rounded-lg overflow-hidden bg-court-800 flex-shrink-0 border border-court-700">
          <img
            src={player.img_url}
            alt={player.player_name}
            className="w-full h-full object-cover object-top"
            onError={e => { e.target.src = `https://placehold.co/48/0d1f35/slate?text=${player.position}`}}
          />
        </div>

        {/* Name + badges */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-body font-semibold text-white truncate">{player.player_name}</span>
            <span className="text-[10px] text-slate-500 font-mono">{player.position}</span>
            {player.injury_status && (
              <span className={clsx(
                'text-[10px] font-mono px-1.5 py-0.5 rounded',
                player.injury_status === 'O' ? 'bg-red-500/20 text-red-400' :
                'bg-yellow-500/20 text-yellow-400'
              )}>
                {player.injury_status}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-xs text-slate-500 font-mono">{player.team}</span>
            <span className="text-xs text-slate-500">
              <span className="text-brand font-semibold">{player.games_this_week}</span> games
            </span>
            <span className="text-xs text-slate-500">
              {player.avg_fantasy_pts} fpts/g
            </span>
          </div>
        </div>

        {/* Score ring + badge */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <RecommendationBadge rec={player.stream_recommendation} />
          <ScoreRing score={player.stream_score} />
        </div>
      </div>

      {/* Week calendar */}
      <WeekCalendar schedule={player.schedule || []} />

      {/* Expanded score breakdown */}
      {expanded && (
        <div className="mt-3 pt-3 border-t border-court-700 fade-up">
          <p className="text-xs text-slate-500 mb-2 flex items-center gap-1">
            <Zap size={11} /> Score breakdown
          </p>
          <ScoreBreakdown breakdown={player.score_breakdown} total={player.stream_score} />
        </div>
      )}
    </div>
  )
}

function ScoreBreakdown({ breakdown, total }) {
  const items = [
    { label: 'Games × 3', value: breakdown?.games_component, positive: true },
    { label: 'Avg FPts × 1.5', value: breakdown?.avg_pts_component, positive: true },
    { label: 'B2B penalty', value: breakdown?.b2b_penalty, positive: false },
    { label: 'Schedule bonus', value: breakdown?.schedule_bonus, positive: breakdown?.schedule_bonus >= 0 },
    { label: 'Injury penalty', value: breakdown?.injury_penalty, positive: false },
  ]

  return (
    <div className="space-y-1.5">
      {items.map(item => item.value !== undefined && (
        <div key={item.label} className="flex items-center justify-between text-xs">
          <span className="text-slate-500">{item.label}</span>
          <span className={clsx(
            'font-mono font-medium',
            item.value > 0 ? 'text-green-400' : item.value < 0 ? 'text-red-400' : 'text-slate-500'
          )}>
            {item.value > 0 ? '+' : ''}{item.value}
          </span>
        </div>
      ))}
      <div className="flex items-center justify-between text-xs pt-1 border-t border-court-700">
        <span className="text-white font-medium">Total</span>
        <span className="font-mono font-bold text-brand">{total}</span>
      </div>
    </div>
  )
}

function FormulaTooltip() {
  const [show, setShow] = useState(false)
  return (
    <div className="relative">
      <button
        className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-brand transition-colors"
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
      >
        <Info size={13} /> How scores work
      </button>
      {show && (
        <div className="absolute right-0 top-full mt-2 w-72 card p-4 text-xs text-slate-300 z-30 shadow-xl shadow-black/50">
          <p className="font-mono text-brand mb-2">Stream Score Formula</p>
          <div className="font-mono text-[11px] space-y-1 text-slate-400">
            <div>+ games_this_week × <span className="text-white">3.0</span></div>
            <div>+ avg_fantasy_pts × <span className="text-white">1.5</span></div>
            <div>− back_to_back_count × <span className="text-white">2.0</span></div>
            <div>+ schedule_bonus <span className="text-green-400">(+3 soft D)</span></div>
            <div>− injury_penalty <span className="text-red-400">(-5 Q / -10 O)</span></div>
          </div>
          <p className="text-slate-500 mt-2">
            <span className="text-green-400">Green = A matchup</span> (bottom-10 D) •{' '}
            <span className="text-yellow-400">B2B</span> = back-to-back rest risk
          </p>
        </div>
      )}
    </div>
  )
}

function ScheduleSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="card p-4 animate-pulse">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-lg bg-court-800" />
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-court-800 rounded w-32" />
              <div className="h-3 bg-court-800 rounded w-24" />
            </div>
            <div className="w-12 h-12 rounded-full bg-court-800" />
          </div>
          <div className="grid grid-cols-7 gap-1 mt-3">
            {Array.from({ length: 7 }).map((_, j) => (
              <div key={j} className="h-12 bg-court-800 rounded" />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
