import { useQuery } from '@tanstack/react-query'
import { getWaiverTargets } from '../lib/api'
import { ScoreRing, RecommendationBadge } from './ScoreComponents'
import { TrendingUp, Zap } from 'lucide-react'
import { clsx } from 'clsx'

export function WaiverTargets({ sessionId }) {
  const { data, isLoading } = useQuery({
    queryKey: ['waiver', sessionId],
    queryFn: () => getWaiverTargets(sessionId).then(r => r.data),
    enabled: !!sessionId,
    staleTime: 120000,
    refetchInterval: 600000, // 10 min
  })

  const targets = data?.targets || []
  const cutoff = data?.ownership_cutoff || 130
  const leagueSize = data?.league_size || 10

  if (isLoading) return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 mb-4">
        <h2 className="font-display text-2xl text-white tracking-wider">WAIVER WIRE</h2>
      </div>
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="card p-4 animate-pulse flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-court-800" />
          <div className="flex-1 space-y-2">
            <div className="h-4 bg-court-800 rounded w-28" />
            <div className="h-3 bg-court-800 rounded w-20" />
          </div>
          <div className="w-10 h-10 rounded-full bg-court-800" />
        </div>
      ))}
    </div>
  )

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="font-display text-2xl text-white tracking-wider">WAIVER WIRE</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {leagueSize}-team league · Players ranked #{cutoff + 1}+ likely available
          </p>
        </div>
      </div>

      {targets.length === 0 ? (
        <div className="card p-10 text-center text-slate-500">
          Loading waiver data from NBA API...
        </div>
      ) : (
        targets.map((p, i) => (
          <WaiverCard key={p.nba_player_id} player={p} rank={i + 1} />
        ))
      )}
    </div>
  )
}

function WaiverCard({ player, rank }) {
  const score = player.stream_score

  return (
    <div className="card-hover p-4 fade-up">
      <div className="flex items-center gap-3">
        {/* Rank */}
        <span className="text-slate-600 font-mono text-xs w-4 flex-shrink-0">#{rank}</span>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-body font-semibold text-white truncate">{player.player_name}</span>
            {player.trending_adds > 0 && (
              <span className="flex items-center gap-0.5 text-[10px] text-brand font-mono">
                <TrendingUp size={10} /> {player.trending_adds} adds
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-1 text-xs text-slate-500 font-mono">
            <span>{player.team}</span>
            <span>
              <span className="text-brand font-semibold">{player.games_this_week}G</span> this week
            </span>
            <span>{player.avg_fantasy_pts} fp/g</span>
          </div>

          {/* Mini breakdown */}
          <div className="flex items-center gap-2 mt-2">
            <ScoreChip label="Games" value={`+${player.score_breakdown?.games_component}`} positive />
            <ScoreChip label="Pts" value={`+${player.score_breakdown?.avg_pts_component}`} positive />
            {player.score_breakdown?.schedule_bonus !== 0 && (
              <ScoreChip
                label="Sched"
                value={`${player.score_breakdown?.schedule_bonus > 0 ? '+' : ''}${player.score_breakdown?.schedule_bonus}`}
                positive={player.score_breakdown?.schedule_bonus > 0}
              />
            )}
          </div>
        </div>

        <div className="flex-shrink-0 flex flex-col items-center gap-2">
          <ScoreRing score={score} size={44} />
          <span className={clsx(
            'text-[9px] font-mono',
            score >= 40 ? 'text-green-400' : 'text-slate-500'
          )}>
            {score >= 50 ? 'HOT' : score >= 35 ? 'STREAM' : 'FRINGE'}
          </span>
        </div>
      </div>
    </div>
  )
}

function ScoreChip({ label, value, positive }) {
  return (
    <span className={clsx(
      'text-[10px] font-mono px-1.5 py-0.5 rounded',
      positive ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
    )}>
      {value}
    </span>
  )
}
