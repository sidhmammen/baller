# Baller - Fantasy NBA Streaming Assistant

A full-stack web app for daily fantasy basketball streaming decisions and pre-game lineup alerts, built for Sleeper leagues.

## Stack
- **Backend**: Python + FastAPI + PostgreSQL + Redis + APScheduler + WebSockets
- **Frontend**: React (Vite) + Tailwind CSS + React Query
- **Data**: Sleeper API (roster/player data) + nba_api (schedules, defensive ratings, live lineups)

---

## Quick Start

### Prerequisites
- Docker + Docker Compose installed

### 1. Clone and run
```bash
git clone <your-repo>
cd fantasy-nba
docker compose up --build
```

### 2. Open the app
Go to `http://localhost:3000`

### 3. Set up your roster
- Option A: Enter your Sleeper username → select your league → auto-import roster
- Option B: Manually search and pick players

---

## How to Test Each Feature

### ✅ Backend health check
```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

### ✅ Player search working
```bash
curl "http://localhost:8000/players/search?q=lebron"
# → array of player objects with img_url
```

### ✅ Sleeper integration
```bash
curl "http://localhost:8000/sleeper/user/YOUR_SLEEPER_USERNAME"
# → {user_id, display_name, ...}

curl "http://localhost:8000/sleeper/user/YOUR_SLEEPER_USERNAME/leagues"
# → array of your NBA leagues
```

### ✅ Roster setup (manual)
```bash
curl -X POST http://localhost:8000/roster/setup \
  -H "Content-Type: application/json" \
  -d '{"player_ids": ["3704","1254"], "league_size": 10, "scoring_type": "points_h2h"}'
# → {session_id, players, ...}
```

### ✅ Weekly schedule + stream scores
```bash
curl "http://localhost:8000/schedule/YOUR_SESSION_ID"
# → {players: [{player_name, stream_score, schedule, score_breakdown, ...}]}
```

### ✅ Waiver targets
```bash
curl "http://localhost:8000/schedule/YOUR_SESSION_ID/waiver"
# → {targets: [{player_name, stream_score, games_this_week, ...}]}
```

### ✅ WebSocket connection
Open browser console at localhost:3000, look for:
```
[ws] Connected
```
The green LIVE indicator in the header confirms connection.

### ✅ Today's games live
```bash
curl "http://localhost:8000/notifications/games/today"
# → {games: [{home_team, away_team, status, ...}]}
```

---

## Architecture Notes

### Stream Score Formula
```
score = (games_this_week × 3.0)
      + (avg_fantasy_pts × 1.5)
      - (back_to_back_count × 2.0)
      + (schedule_bonus: +3 facing bottom-10 D, -2 facing top-10 D)
      - (injury_penalty: -5 Q/GTD, -10 O/IR)
```
The formula breakdown is visible in the UI for every player. Click any player card to expand.

### Lineup Alerts
- APScheduler checks for upcoming games every 30 minutes
- When a game is within 2 hours, switches to 5-minute polling
- Uses `nba_api.live.nba.endpoints.boxscore` for confirmed starters
- Publishes to Redis channel `lineup_alerts`
- FastAPI WebSocket subscribed to Redis channel broadcasts to connected clients instantly

### Ownership Estimation
```
6 teams  × 13 spots ≈ 78 players owned → #79+ likely available
8 teams  × 13 spots ≈ 104 players owned → #105+ likely available
10 teams × 13 spots ≈ 130 players owned → #131+ likely available
12 teams × 13 spots ≈ 156 players owned → #157+ likely available
14 teams × 13 spots ≈ 182 players owned → #183+ likely available
```
Rankings are based on NBA API season fantasy point averages (Sleeper scoring format).

---

## Common Gotchas

### nba_api rate limits
The library uses the NBA stats site which has aggressive rate limiting. We sleep 0.6s between calls and cache everything in Redis. If you see 429 errors:
- Increase sleep to 1.0s in `services/nba_data.py`  
- The first cold start will be slow — all caches are warming up

### Sleeper player IDs vs NBA API player IDs
These are **different ID systems**. Sleeper uses their own string IDs. NBA API uses NBA.com numeric IDs. The bridge is done by name matching in `routers/schedule.py`. For players with common names or name variations this occasionally mismatches — a production fix would be to maintain a mapping table.

### WebSocket in Docker
If WebSocket shows as offline, check that the `VITE_WS_URL` env var is set correctly. When running in Docker, the frontend connects to `ws://localhost:8000` (your machine), not `ws://backend:8000` (Docker internal).

### Lineup data availability
NBA starting lineups are officially released ~60–90 minutes before tip-off. The `nba_api` boxscore endpoint only has starters once the game starts or is within the official window. For earlier lineup news, Twitter/X accounts like @LineupIQ post them faster — you'd scrape those for a production upgrade.
