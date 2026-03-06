import { clsx } from 'clsx'

// Circular SVG score ring
export function ScoreRing({ score, max = 80, size = 52 }) {
  const pct = Math.min(score / max, 1)
  const r = (size - 6) / 2
  const circ = 2 * Math.PI * r
  const offset = circ * (1 - pct)

  const color = score >= 55 ? '#22c55e'
    : score >= 40 ? '#f97316'
    : score >= 25 ? '#94a3b8'
    : '#ef4444'

  return (
    <div className="relative flex-shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke="#1e2d3d" strokeWidth={4}
        />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke={color} strokeWidth={4}
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          className="score-ring"
        />
      </svg>
      <span
        className="absolute inset-0 flex items-center justify-center text-xs font-mono font-semibold"
        style={{ color }}
      >
        {Math.round(score)}
      </span>
    </div>
  )
}

const RECOMMENDATION_CONFIG = {
  MUST_PLAY: { label: 'MUST PLAY', cls: 'badge-green' },
  STREAM: { label: 'STREAM', cls: 'badge-orange' },
  SIT: { label: 'SIT', cls: 'badge-gray' },
  DROP: { label: 'DROP', cls: 'bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-mono px-2 py-0.5 rounded-full' },
  QUESTIONABLE: { label: 'GTD', cls: 'badge-orange' },
  OUT: { label: 'OUT', cls: 'badge-red' },
}

export function RecommendationBadge({ rec }) {
  const config = RECOMMENDATION_CONFIG[rec] || { label: rec, cls: 'badge-gray' }
  return <span className={config.cls}>{config.label}</span>
}

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export function WeekCalendar({ schedule }) {
  const today = new Date()
  const monday = new Date(today)
  monday.setDate(today.getDate() - ((today.getDay() + 6) % 7))

  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday)
    d.setDate(monday.getDate() + i)
    return d
  })

  const gamesByDate = {}
  for (const g of schedule) {
    const key = g.game_date?.split('T')[0] || g.game_date
    gamesByDate[key] = g
  }

  return (
    <div className="grid grid-cols-7 gap-1 mt-2">
      {days.map((d, i) => {
        const fmt = (dt) => {
          const y = dt.getFullYear()
          const m = String(dt.getMonth() + 1).padStart(2, '0')
          const day = String(dt.getDate()).padStart(2, '0')
          return `${y}-${m}-${day}`
        }

        const key = fmt(d)
        const isToday = key === fmt(today)
        const game = gamesByDate[key]
        const isPast = d < today && !isToday

        return (
          <div
            key={i}
            className={clsx(
              'flex flex-col items-center gap-1 py-1.5 px-1 rounded-md text-[10px]',
              isToday && 'ring-1 ring-brand/40',
              isPast && !game && 'opacity-20',
              game
                ? game.is_back_to_back
                  ? 'bg-yellow-500/10 border border-yellow-500/20'
                  : game.matchup_grade === 'A'
                    ? 'bg-green-500/10 border border-green-500/20'
                    : game.matchup_grade === 'C'
                      ? 'bg-slate-800/50 border border-slate-700/30'
                      : 'bg-court-800 border border-court-700'
                : 'bg-transparent border border-transparent',
            )}
          >
            <span className="text-slate-500 font-body">{DAY_LABELS[i]}</span>
            {game ? (
              <>
                <span className={clsx(
                  'font-mono font-semibold',
                  game.matchup_grade === 'A' ? 'text-green-400' :
                  game.matchup_grade === 'C' ? 'text-slate-400' : 'text-white'
                )}>
                  {game.opponent}
                </span>
                {game.is_back_to_back && <span className="text-yellow-400 text-[8px]">B2B</span>}
                {game.matchup_grade === 'A' && !game.is_back_to_back && (
                  <span className="text-green-400 text-[8px]">A</span>
                )}
              </>
            ) : (
              <span className="text-slate-700">—</span>
            )}
          </div>
        )
      })}
    </div>
  )
}