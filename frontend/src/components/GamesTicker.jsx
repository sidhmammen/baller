import { clsx } from 'clsx'

export function GamesTicker({ games }) {
  if (!games || games.length === 0) return null

  return (
    <div className="overflow-x-auto scrollbar-none">
      <div className="flex gap-2 pb-1" style={{ minWidth: 'max-content' }}>
        {games.map(g => (
          <GameChip
              key={g.game_id || `${g.away_team}-${g.home_team}-${g.game_time_utc || g.status || ''}`}
              game={g}
            />
        ))}
      </div>
    </div>
  )
}

function GameChip({ game }) {
  const isLive = game.status_code === 2
  const isFinal = game.status_code === 3

  return (
    <div className={clsx(
      'flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-mono',
      isLive
        ? 'bg-green-500/10 border-green-500/30 text-green-300'
        : isFinal
          ? 'bg-slate-800/50 border-slate-700/30 text-slate-500'
          : 'bg-court-900 border-court-700 text-slate-400',
    )}>
      {isLive && (
        <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
      )}
      <span>{game.away_team}</span>
      {(isLive || isFinal) ? (
        <>
          <span className="text-white font-bold">{game.away_score}</span>
          <span className="text-slate-600">—</span>
          <span className="text-white font-bold">{game.home_score}</span>
        </>
      ) : (
        <span className="text-slate-600">@</span>
      )}
      <span>{game.home_team}</span>
      {isLive && <span className="text-green-400 text-[10px]">{game.status}</span>}
      {!isLive && !isFinal && (
        <span className="text-slate-500 text-[10px]">
          {game.game_time_est ? game.game_time_est.split('T')[1]?.slice(0, 5) : game.status}
        </span>
      )}
    </div>
  )
}
