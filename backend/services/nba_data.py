"""
NBA data via nba_api (best coverage) BUT with cache-first design.

Important rule for this app:
- /schedule endpoint must NEVER block on NBA API calls.
So:
- `get_*_cached()` = Redis only (safe for /schedule)
- `ensure_*_cached()` = can call nba_api and populate Redis (call from roster prewarm)

If nba_api is blocked inside Docker for you, run the backend locally (venv) and keep
Redis/Postgres in Docker. This file will still work.
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import pytz

from redis_client import cache_get, cache_set, TTL_SCHEDULE, TTL_DEF_RATINGS, TTL_LIVE_SCOREBOARD

from nba_api.stats.endpoints import (
    leaguegamefinder,
    leaguedashteamstats,
    leaguedashplayerstats,
)
from nba_api.live.nba.endpoints import scoreboard as live_scoreboard, boxscore as live_boxscore
import httpx

async def _get_full_schedule_cdn() -> list[dict]:
    cached = await cache_get("nba:full_schedule_cdn")
    if cached:
        return cached

    url = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    game_dates = data.get("leagueSchedule", {}).get("gameDates", [])
    games: list[dict] = []
    for gd in game_dates:
        games.extend(gd.get("games", []) or [])

    await cache_set("nba:full_schedule_cdn", games, 21600)  # 6h
    return games

EASTERN = pytz.timezone("America/New_York")

TEAM_ABB_TO_ID: Dict[str, int] = {
    "ATL": 1610612737, "BOS": 1610612738, "BKN": 1610612751, "CHA": 1610612766,
    "CHI": 1610612741, "CLE": 1610612739, "DAL": 1610612742, "DEN": 1610612743,
    "DET": 1610612765, "GSW": 1610612744, "HOU": 1610612745, "IND": 1610612754,
    "LAC": 1610612746, "LAL": 1610612747, "MEM": 1610612763, "MIA": 1610612748,
    "MIL": 1610612749, "MIN": 1610612750, "NOP": 1610612740, "NYK": 1610612752,
    "OKC": 1610612760, "ORL": 1610612753, "PHI": 1610612755, "PHX": 1610612756,
    "POR": 1610612757, "SAC": 1610612758, "SAS": 1610612759, "TOR": 1610612761,
    "UTA": 1610612762, "WAS": 1610612764,
}

ID_TO_ABB = {v: k for k, v in TEAM_ABB_TO_ID.items()}

def _sleep():
    time.sleep(0.6)

def _week_bounds_et(now: Optional[datetime] = None) -> Tuple[datetime.date, datetime.date, str]:
    """Return (monday, sunday, week_key) in ET."""
    dt = now or datetime.now(EASTERN)
    today = dt.date()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday, monday.strftime("%Y-%m-%d")

def normalize_player_name(name: str) -> str:
    import unicodedata, re
    s = (name or "").strip().lower()
    s = "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    toks = [t for t in s.split() if t not in {"jr", "sr", "ii", "iii", "iv", "v"}]
    return " ".join(toks)

# -----------------------------------------------------------------------------
# Cache-only getters (SAFE FOR /schedule)
# -----------------------------------------------------------------------------

async def get_team_schedule_cached(team_abbr: str, week_key: Optional[str] = None) -> List[dict]:
    _, _, wk = _week_bounds_et()
    wk = week_key or wk
    cache_key = f"schedule:week2:{team_abbr}:{wk}"
    return (await cache_get(cache_key)) or []

async def get_team_def_ratings_cached() -> Dict[str, dict]:
    return (await cache_get("nba:def_ratings")) or {}

async def get_player_season_averages_cached() -> Dict[str, dict]:
    return (await cache_get("nba:player_avgs")) or {}

async def get_player_name_map_cached() -> Dict[str, str]:
    return (await cache_get("nba:player_avgs_by_name")) or {}

# -----------------------------------------------------------------------------
# Ensure cache (CAN CALL NBA API) – call from roster prewarm
# -----------------------------------------------------------------------------

async def ensure_team_schedule_cached(team_abbr: str) -> List[dict]:
    monday, sunday, week_key = _week_bounds_et()
    cache_key = f"schedule:week2:{team_abbr}:{week_key}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    team_id = TEAM_ABB_TO_ID.get(team_abbr)
    if not team_id:
        await cache_set(cache_key, [], TTL_SCHEDULE)
        return []

    games_all = await _get_full_schedule_cdn()
    print("[cdn] sample homeTeam keys:", list((games_all[0].get("homeTeam") or {}).keys()) if games_all else [],
          flush=True)

    def _team_id(team_obj: dict) -> Optional[int]:
        if not team_obj:
            return None
        tid = team_obj.get("teamId") or team_obj.get("teamID") or team_obj.get("id")
        try:
            return int(tid)
        except Exception:
            return None

    games: List[dict] = []
    for g in games_all:
        home_obj = g.get("homeTeam") or {}
        away_obj = g.get("awayTeam") or {}

        home_id = _team_id(home_obj)
        away_id = _team_id(away_obj)
        if team_id not in (home_id, away_id):
            continue

        if len(games) == 0 and (g.get("gameDateEst") or g.get("gameTimeUTC")):
            print(
                f"[cdn] date fields est={g.get('gameDateEst')} utc={g.get('gameDateUTC')} time={g.get('gameTimeUTC')}",
                flush=True)

        date_str = (
                g.get("gameDateEst")
                or g.get("gameDateUTC")
                or g.get("gameDate")
                or ""
        )

        game_date = None
        if date_str:
            # Usually "2026-03-06"
            try:
                game_date = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
            except Exception:
                game_date = None

        # Fallback to gameTimeUTC parsing only if needed
        if game_date is None:
            game_time_utc = g.get("gameTimeUTC") or g.get("gameTimeUtc") or ""
            if not game_time_utc:
                continue
            try:
                dt_et = datetime.fromisoformat(game_time_utc.replace("Z", "+00:00")).astimezone(EASTERN)
                game_date = dt_et.date()
            except Exception:
                continue

        if not (monday <= game_date <= sunday):
            continue

        opp_id = away_id if team_id == home_id else home_id
        opponent = ID_TO_ABB.get(opp_id, "") if opp_id else ""

        home_tri = ID_TO_ABB.get(home_id, "") if home_id else ""
        away_tri = ID_TO_ABB.get(away_id, "") if away_id else ""


        games.append({
            "game_id": str(g.get("gameId") or ""),
            "game_date": game_date.strftime("%Y-%m-%d"),
            "matchup": f"{away_tri} @ {home_tri}",
            "is_home": team_id == home_id,
            "opponent": opponent,
            "wl": "",
        })

    games.sort(key=lambda x: (x["game_date"], x.get("game_id", "")))
    await cache_set(cache_key, games, TTL_SCHEDULE)
    print(f"[cdn] cached {team_abbr} week={week_key} games={len(games)}", flush=True)
    return games

async def ensure_team_def_ratings_cached(season: str = "2024-25") -> Dict[str, dict]:
    cached = await cache_get("nba:def_ratings")
    if cached:
        return cached

    def _fetch():
        _sleep()
        try:
            stats = leaguedashteamstats.LeagueDashTeamStats(season=season)
            df = stats.get_data_frames()[0]

            # Prefer DEF_RATING if present; otherwise fallback to OPP_PTS (rough)
            if "DEF_RATING" in df.columns:
                df_sorted = df.sort_values("DEF_RATING", ascending=True).reset_index(drop=True)
                def_col = "DEF_RATING"
            elif "OPP_PTS" in df.columns:
                df_sorted = df.sort_values("OPP_PTS", ascending=True).reset_index(drop=True)
                def_col = "OPP_PTS"
            else:
                # fallback neutral
                return {}

            result = {}
            for idx, row in df_sorted.iterrows():
                abbr = str(row.get("TEAM_ABBREVIATION", ""))
                result[abbr] = {
                    "def_value": round(float(row.get(def_col, 0) or 0), 2),
                    "def_rank": idx + 1,
                    "team_name": str(row.get("TEAM_NAME", "")),
                }
            return result
        except Exception as e:
            print(f"[def_ratings] nba_api fetch failed: {e}", flush=True)
            return {}

    loop = asyncio.get_event_loop()
    ratings = await loop.run_in_executor(None, _fetch)
    if not ratings:
        # Neutral fallback so UI still works
        ratings = {abbr: {"opp_pts": 110.0, "def_rank": 15, "team_name": abbr} for abbr in TEAM_ABB_TO_ID.keys()}
    await cache_set("nba:def_ratings", ratings, TTL_DEF_RATINGS)
    return ratings

async def ensure_player_season_averages_cached(season: str = "2024-25") -> Dict[str, dict]:
    cached = await cache_get("nba:player_avgs")
    cached_names = await cache_get("nba:player_avgs_by_name")
    if cached and cached_names:
        return cached

    def _fetch():
        _sleep()
        try:
            stats = leaguedashplayerstats.LeagueDashPlayerStats(season=season)
            df = stats.get_data_frames()[0]

            avgs, name_map = {}, {}
            for _, row in df.iterrows():
                pid = str(row.get("PLAYER_ID", ""))
                name = str(row.get("PLAYER_NAME", ""))

                # nba_api usually returns per-game columns (PTS, REB, AST, STL, BLK, TOV)
                gp = int(row.get("GP", 0) or 0)
                if gp <= 0:
                    continue

                # Treat these as TOTALS
                pts_t = float(row.get("PTS", 0) or 0)
                reb_t = float(row.get("REB", 0) or 0)
                ast_t = float(row.get("AST", 0) or 0)
                stl_t = float(row.get("STL", 0) or 0)
                blk_t = float(row.get("BLK", 0) or 0)
                tov_t = float(row.get("TOV", 0) or 0)

                fantasy_total = pts_t + (reb_t * 1.2) + (ast_t * 1.5) + (stl_t * 3) + (blk_t * 3) - tov_t
                fantasy_pts = fantasy_total / gp  # PER GAME

                avgs[pid] = {
                    "fantasy_pts": round(fantasy_pts, 1),
                    "gp": gp,
                    "name": name,
                    "team": str(row.get("TEAM_ABBREVIATION", "")),
                }
                if name:
                    name_map[normalize_player_name(name)] = pid

            return avgs, name_map

        except Exception as e:
            print(f"[player_avgs] nba_api fetch failed: {e}", flush=True)
            return {}, {}

    loop = asyncio.get_event_loop()
    avgs, name_map = await loop.run_in_executor(None, _fetch)

    # If fetch failed, keep caches short so we retry soon (don’t “poison” cache)
    if not avgs:
        await cache_set("nba:player_avgs", {}, 300)
        await cache_set("nba:player_avgs_by_name", {}, 300)
        return {}

    await cache_set("nba:player_avgs", avgs, 7200)
    await cache_set("nba:player_avgs_by_name", name_map, 7200)
    return avgs

# -----------------------------------------------------------------------------
# Live scoreboard + starters (nba_api.live usually OK)
# -----------------------------------------------------------------------------

async def get_live_scoreboard() -> dict:
    cached = await cache_get("nba:live_scoreboard")
    if cached:
        return cached

    def _fetch():
        try:
            board = live_scoreboard.ScoreBoard()
            return board.get_dict()
        except Exception as e:
            print(f"[live_scoreboard] Error: {e}", flush=True)
            return {}

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, _fetch)
    await cache_set("nba:live_scoreboard", data, TTL_LIVE_SCOREBOARD)
    return data

async def get_game_starters(game_id: str) -> dict:
    cache_key = f"nba:starters:{game_id}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    def _fetch():
        try:
            box = live_boxscore.BoxScore(game_id=game_id)
            data = box.get_dict()
            game = data.get("game", {})

            def _team_starters(team_key: str) -> List[dict]:
                team = game.get(team_key, {})
                players = team.get("players", []) or []
                return [{
                    "player_id": str(p.get("personId", "")),
                    "name": p.get("name", ""),
                    "starter": (p.get("starter", "0") == "1"),
                    "status": p.get("status", ""),
                } for p in players]

            return {"home": _team_starters("homeTeam"), "away": _team_starters("awayTeam")}
        except Exception as e:
            print(f"[starters] Error for game {game_id}: {e}", flush=True)
            return {"home": [], "away": []}

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _fetch)
    await cache_set(cache_key, result, 120)
    return result

async def get_todays_games() -> List[dict]:
    cached = await cache_get("nba:today_games")
    if cached:
        return cached

    board = await get_live_scoreboard()
    games: List[dict] = []
    try:
        game_list = board.get("scoreboard", {}).get("games", []) or []
        for g in game_list:
            games.append({
                "game_id": g.get("gameId", ""),
                "status": g.get("gameStatusText", ""),
                "status_code": g.get("gameStatus", 1),
                "home_team": (g.get("homeTeam") or {}).get("teamTricode", ""),
                "away_team": (g.get("awayTeam") or {}).get("teamTricode", ""),
                "home_score": (g.get("homeTeam") or {}).get("score", 0),
                "away_score": (g.get("awayTeam") or {}).get("score", 0),
                "game_time_utc": g.get("gameTimeUTC", ""),
                "game_time_est": g.get("gameEt", ""),
            })
    except Exception as e:
        print(f"[today_games] Parse error: {e}", flush=True)

    await cache_set("nba:today_games", games, 300)
    return games