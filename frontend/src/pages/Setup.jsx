import { useState, useEffect, useRef } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { lookupSleeperUser, getSleeperLeagues, setupRoster, searchPlayers } from '../lib/api'
import { useSetupRoster, useSessionId } from '../hooks/useRoster'
import { Search, Check, X, ChevronRight, Users, Loader2, Zap } from 'lucide-react'
import { clsx } from 'clsx'

export function Setup({ onComplete }) {
  const [mode, setMode] = useState('choose') // 'choose' | 'sleeper' | 'manual'

  if (mode === 'choose') return <ModeChooser onMode={setMode} />
  if (mode === 'sleeper') return <SleeperImport onComplete={onComplete} />
  if (mode === 'manual') return <ManualPicker onComplete={onComplete} />
}

function ModeChooser({ onMode }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-16">
      <div className="text-center mb-12">
        <h1 className="font-display text-6xl text-white tracking-widest mb-3">HOOPSTREAM</h1>
        <p className="text-slate-400 text-lg">Daily streaming decisions + pre-game lineup alerts</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-xl">
        <ModeCard
          icon="🏀"
          title="Import from Sleeper"
          desc="Connect your Sleeper username and we'll pull your roster automatically"
          badge="Recommended"
          onClick={() => onMode('sleeper')}
        />
        <ModeCard
          icon="✏️"
          title="Build manually"
          desc="Search and pick players one by one"
          onClick={() => onMode('manual')}
        />
      </div>
    </div>
  )
}

function ModeCard({ icon, title, desc, badge, onClick }) {
  return (
    <button
      onClick={onClick}
      className="card-hover p-6 text-left flex flex-col gap-3 group"
    >
      <div className="flex items-start justify-between">
        <span className="text-3xl">{icon}</span>
        {badge && <span className="badge-orange">{badge}</span>}
      </div>
      <div>
        <h3 className="font-body font-semibold text-white group-hover:text-brand transition-colors">
          {title}
        </h3>
        <p className="text-sm text-slate-500 mt-1">{desc}</p>
      </div>
      <ChevronRight size={16} className="text-slate-600 group-hover:text-brand transition-colors" />
    </button>
  )
}

// --------------- Sleeper Import ---------------

function SleeperImport({ onComplete }) {
  const [username, setUsername] = useState('')
  const [submittedUser, setSubmittedUser] = useState('')
  const [selectedLeague, setSelectedLeague] = useState(null)
  const [leagueSize, setLeagueSize] = useState(10)
  const [scoringType, setScoringType] = useState('points_h2h')
  const { saveSession } = useSessionId()
  const setupMutation = useSetupRoster()

  const userQuery = useQuery({
    queryKey: ['sleeper_user', submittedUser],
    queryFn: () => lookupSleeperUser(submittedUser).then(r => r.data),
    enabled: !!submittedUser,
  })

  const leaguesQuery = useQuery({
    queryKey: ['sleeper_leagues', submittedUser],
    queryFn: () => getSleeperLeagues(submittedUser).then(r => r.data),
    enabled: !!userQuery.data,
  })

  const handleImport = async () => {
    if (!selectedLeague) return
    try {
      const res = await setupMutation.mutateAsync({
        sleeper_username: submittedUser,
        sleeper_league_id: selectedLeague.league_id,
        league_size: leagueSize,
        scoring_type: scoringType,
      })
      saveSession(res.data.session_id)
      onComplete(res.data.session_id)
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-16">
      <div className="w-full max-w-lg space-y-6">
        <div>
          <h2 className="font-display text-4xl text-white tracking-wider">IMPORT FROM SLEEPER</h2>
          <p className="text-slate-500 text-sm mt-1">Enter your Sleeper username to fetch your leagues</p>
        </div>

        {/* Username input */}
        <div className="flex gap-2">
          <input
            className="flex-1 bg-court-900 border border-court-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-600 focus:outline-none focus:border-brand/60 text-sm"
            placeholder="your sleeper username"
            value={username}
            onChange={e => setUsername(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && setSubmittedUser(username)}
          />
          <button
            className="btn-primary"
            onClick={() => setSubmittedUser(username)}
          >
            Look up
          </button>
        </div>

        {/* User found */}
        {userQuery.isError && (
          <p className="text-red-400 text-sm">User not found. Check your username and try again.</p>
        )}

        {userQuery.data && (
          <div className="card p-4 flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-brand/20 flex items-center justify-center text-brand font-bold text-sm">
              {userQuery.data.display_name?.[0]?.toUpperCase()}
            </div>
            <div>
              <p className="text-white font-medium text-sm">{userQuery.data.display_name}</p>
              <p className="text-slate-500 text-xs">Sleeper user found ✓</p>
            </div>
          </div>
        )}

        {/* Leagues */}
        {leaguesQuery.isLoading && (
          <div className="flex items-center gap-2 text-slate-500 text-sm">
            <Loader2 size={14} className="animate-spin" /> Fetching your leagues...
          </div>
        )}

        {leaguesQuery.data && leaguesQuery.data.length === 0 && (
          <p className="text-slate-500 text-sm">No NBA leagues found for this account in 2024.</p>
        )}

        {leaguesQuery.data && leaguesQuery.data.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs text-slate-500 uppercase tracking-wider">Select your league</p>
            {leaguesQuery.data.map(league => (
              <button
                key={league.league_id}
                onClick={() => {
                  setSelectedLeague(league)
                  setLeagueSize(league.total_rosters || 10)
                }}
                className={clsx(
                  'w-full card p-4 text-left flex items-center justify-between transition-all',
                  selectedLeague?.league_id === league.league_id
                    ? 'border-brand/60 bg-brand/5'
                    : 'hover:border-court-600',
                )}
              >
                <div>
                  <p className="text-white font-medium text-sm">{league.name}</p>
                  <p className="text-slate-500 text-xs">{league.total_rosters} teams · {league.status}</p>
                </div>
                {selectedLeague?.league_id === league.league_id && (
                  <Check size={16} className="text-brand" />
                )}
              </button>
            ))}
          </div>
        )}

        {/* League config */}
        {selectedLeague && (
          <div className="space-y-4 fade-up">
            <div>
              <label className="text-xs text-slate-500 uppercase tracking-wider mb-2 block">Scoring type</label>
              <div className="flex gap-2">
                {[
                  { v: 'points_h2h', label: 'Points H2H' },
                  { v: 'categories_h2h', label: 'Cat H2H', disabled: true },
                  { v: 'categories_roto', label: 'Roto', disabled: true },
                ].map(opt => (
                  <button
                    key={opt.v}
                    disabled={opt.disabled}
                    onClick={() => setScoringType(opt.v)}
                    className={clsx(
                      'px-3 py-1.5 rounded-lg text-sm border transition-all',
                      opt.disabled && 'opacity-30 cursor-not-allowed',
                      scoringType === opt.v
                        ? 'bg-brand/20 border-brand/60 text-brand'
                        : 'bg-court-900 border-court-700 text-slate-400',
                    )}
                  >
                    {opt.label}
                    {opt.disabled && <span className="text-[10px] ml-1">(soon)</span>}
                  </button>
                ))}
              </div>
            </div>

            <button
              className="btn-primary w-full flex items-center justify-center gap-2"
              onClick={handleImport}
              disabled={setupMutation.isPending}
            >
              {setupMutation.isPending ? (
                <><Loader2 size={16} className="animate-spin" /> Importing roster...</>
              ) : (
                <><Zap size={16} /> Import roster from Sleeper</>
              )}
            </button>

            {setupMutation.isError && (
              <p className="text-red-400 text-sm">Import failed. Check that you're in this league.</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// --------------- Manual Picker ---------------

function ManualPicker({ onComplete }) {
  const [query, setQuery] = useState('')
  const [debouncedQ, setDebouncedQ] = useState('')
  const [selected, setSelected] = useState([]) // [{player_id, full_name, team, position, img_url}]
  const [leagueSize, setLeagueSize] = useState(10)
  const [scoringType, setScoringType] = useState('points_h2h')
  const { saveSession } = useSessionId()
  const setupMutation = useSetupRoster()
  const debounceRef = useRef(null)

  useEffect(() => {
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => setDebouncedQ(query), 300)
  }, [query])

  const searchQuery = useQuery({
    queryKey: ['players_search', debouncedQ],
    queryFn: () => searchPlayers(debouncedQ).then(r => r.data),
    enabled: debouncedQ.length >= 2 || debouncedQ === '',
    staleTime: 60000,
  })

  const players = searchQuery.data || []
  const selectedIds = new Set(selected.map(p => p.player_id))

  const toggle = (p) => {
    if (selectedIds.has(p.player_id)) {
      setSelected(s => s.filter(x => x.player_id !== p.player_id))
    } else if (selected.length < 15) {
      setSelected(s => [...s, p])
    }
  }

  const handleSubmit = async () => {
    if (selected.length === 0) return
    try {
      const res = await setupMutation.mutateAsync({
        player_ids: selected.map(p => p.player_id),
        league_size: leagueSize,
        scoring_type: scoringType,
      })
      saveSession(res.data.session_id)
      onComplete(res.data.session_id)
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center px-4 py-12">
      <div className="w-full max-w-2xl space-y-6">
        <div>
          <h2 className="font-display text-4xl text-white tracking-wider">BUILD YOUR ROSTER</h2>
          <p className="text-slate-500 text-sm mt-1">Pick up to 15 players · {selected.length}/15 selected</p>
        </div>

        {/* League settings */}
        <div className="flex gap-4 flex-wrap">
          <div>
            <label className="text-xs text-slate-500 uppercase tracking-wider mb-1.5 block">League size</label>
            <div className="flex gap-1">
              {[6, 8, 10, 12, 14].map(n => (
                <button
                  key={n}
                  onClick={() => setLeagueSize(n)}
                  className={clsx(
                    'px-3 py-1 rounded text-sm border transition-all',
                    leagueSize === n
                      ? 'bg-brand/20 border-brand/60 text-brand'
                      : 'bg-court-900 border-court-700 text-slate-400',
                  )}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            className="w-full bg-court-900 border border-court-700 rounded-lg pl-9 pr-4 py-2.5 text-white placeholder-slate-600 focus:outline-none focus:border-brand/60 text-sm"
            placeholder="Search players..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            autoFocus
          />
        </div>

        {/* Player grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-96 overflow-y-auto pr-1">
          {players.map(p => {
            const isSelected = selectedIds.has(p.player_id)
            return (
              <button
                key={p.player_id}
                onClick={() => toggle(p)}
                className={clsx(
                  'relative flex items-center gap-2.5 p-2.5 rounded-lg border text-left transition-all',
                  isSelected
                    ? 'bg-brand/10 border-brand/60'
                    : 'bg-court-900 border-court-700 hover:border-court-600',
                )}
              >
                <img
                  src={p.img_url}
                  alt={p.full_name}
                  className="w-9 h-9 rounded-md object-cover object-top bg-court-800 flex-shrink-0"
                  onError={e => { e.target.src = `https://placehold.co/36/0d1f35/slate?text=${p.position}` }}
                />
                <div className="min-w-0">
                  <p className="text-white text-xs font-medium truncate">{p.full_name}</p>
                  <p className="text-slate-500 text-[10px] font-mono">{p.team} · {p.position}</p>
                  {p.injury_status && (
                    <p className="text-yellow-400 text-[10px]">{p.injury_status}</p>
                  )}
                </div>
                {isSelected && (
                  <div className="absolute top-1.5 right-1.5 w-4 h-4 rounded-full bg-brand flex items-center justify-center">
                    <Check size={10} className="text-white" />
                  </div>
                )}
              </button>
            )
          })}
        </div>

        {/* Selected chips */}
        {selected.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {selected.map(p => (
              <span
                key={p.player_id}
                className="flex items-center gap-1.5 bg-court-800 border border-court-700 text-xs px-2.5 py-1 rounded-full text-white"
              >
                {p.full_name}
                <button onClick={() => toggle(p)}>
                  <X size={11} className="text-slate-400 hover:text-red-400" />
                </button>
              </span>
            ))}
          </div>
        )}

        <button
          className="btn-primary w-full flex items-center justify-center gap-2"
          onClick={handleSubmit}
          disabled={selected.length === 0 || setupMutation.isPending}
        >
          {setupMutation.isPending ? (
            <><Loader2 size={16} className="animate-spin" /> Saving roster...</>
          ) : (
            <>Let's go →</>
          )}
        </button>
      </div>
    </div>
  )
}
