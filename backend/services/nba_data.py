"""
NBA data via nba_api library (free, no key needed).
IMPORTANT: Always sleep 0.6s between calls to avoid rate limiting.
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional
import pytz

from redis_client import cache_get, cache_set, TTL_SCHEDULE, TTL_DEF_RATINGS, TTL_LIVE_SCOREBOARD

# nba_api imports — run in thread executor since nba_api is synchronous
from nba_api.stats.endpoints import (
    leaguegamefinder,
    leaguedashteamstats,
    teamgamelog,
    commonteamroster,
    playergamelog,
    leaguedashplayerstats,
)
from nba_api.live.nba.endpoints import scoreboard as live_scoreboard, boxscore as live_boxscore

EASTERN = pytz.timezone("America/New_York")

# Map team abbreviation → NBA team_id for nba_api
TEAM_ABB_TO_ID = {
    "ATL": 1610612737, "BOS": 1610612738, "BKN": 1610612751, "CHA": 1610612766,
    "CHI": 1610612741, "CLE": 1610612739, "DAL": 1610612742, "DEN": 1610612743,
    "DET": 1610612765, "GSW": 1610612744, "HOU": 1610612745, "IND": 1610612754,
    "LAC": 1610612746, "LAL": 1610612747, "MEM": 1610612763, "MIA": 1610612748,
    "MIL": 1610612749, "MIN": 1610612750, "NOP": 1610612740, "NYK": 1610612752,
    "OKC": 1610612760, "ORL": 1610612753, "PHI": 1610612755, "PHX": 1610612756,
    "POR": 1610612757, "SAC": 1610612758, "SAS": 1610612759, "TOR": 1610612761,
    "UTA": 1610612762, "WAS": 1610612764,
}

def _sleep():
    time.sleep(0.6)

# ---------------------------------------------------------------------------
# Weekly schedule helpers
# ---------------------------------------------------------------------------

async def get_team_schedule_this_week(team_abbr: str) -> list[dict]:
    """Return this week's games for a given team abbreviation."""
    cache_key = f"schedule:week:{team_abbr}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    def _fetch():
        _sleep()
        today = datetime.now(EASTERN).date()
        # Monday of current week
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)

        games = []
        try:
            finder = leaguegamefinder.LeagueGameFinder(
                team_id_nullable=TEAM_ABB_TO_ID.get(team_abbr),
                date_from_nullable=monday.strftime("%m/%d/%Y"),
                date_to_nullable=sunday.strftime("%m/%d/%Y"),
                league_id_nullable="00",
            )
            df = finder.get_data_frames()[0]
            for _, row in df.iterrows():
                is_home = "@" not in str(row.get("MATCHUP", ""))
                opp = str(row.get("MATCHUP", "")).split()[-1]
                games.append({
                    "game_id": str(row.get("GAME_ID", "")),
                    "game_date": str(row.get("GAME_DATE", "")),
                    "matchup": str(row.get("MATCHUP", "")),
                    "is_home": is_home,
                    "opponent": opp,
                    "wl": str(row.get("WL", "")),
                })
        except Exception as e:
            print(f"[schedule] Error fetching {team_abbr}: {e}")
        return games

    loop = asyncio.get_event_loop()
    games = await loop.run_in_executor(None, _fetch)
    await cache_set(cache_key, games, TTL_SCHEDULE)
    return games

# ---------------------------------------------------------------------------
# Defensive ratings
# ---------------------------------------------------------------------------

async def get_team_def_ratings() -> dict:
    """Return dict of team_abbr → def_rating (opponent pts per 100 possessions).
    Lower = better defense for the offensive player streaming against them.
    """
    cached = await cache_get("nba:def_ratings")
    if cached:
        return cached

    def _fetch():
        _sleep()
        try:
            stats = leaguedashteamstats.LeagueDashTeamStats(
                season="2024-25",
                per_mode_simple="PerGame",
                measure_type_simple="Defense",
            )
            df = stats.get_data_frames()[0]
            result = {}
            # Rank: 1 = best defense (lowest opp pts), 30 = worst defense
            df_sorted = df.sort_values("OPP_PTS", ascending=True).reset_index(drop=True)
            for idx, row in df_sorted.iterrows():
                abbr = str(row.get("TEAM_ABBREVIATION", ""))
                result[abbr] = {
                    "opp_pts": round(float(row.get("OPP_PTS", 0)), 1),
                    "def_rank": idx + 1,  # 1 = toughest D
                    "team_name": str(row.get("TEAM_NAME", "")),
                }
            return result
        except Exception as e:
            print(f"[def_ratings] Error: {e}")
            return {}

    loop = asyncio.get_event_loop()
    ratings = await loop.run_in_executor(None, _fetch)
    await cache_set("nba:def_ratings", ratings, TTL_DEF_RATINGS)
    return ratings

# ---------------------------------------------------------------------------
# Player season averages
# ---------------------------------------------------------------------------

async def get_player_season_averages() -> dict:
    """Returns dict of nba player_id (str) → avg fantasy pts (points scoring)."""
    cached = await cache_get("nba:player_avgs")
    if cached:
        return cached

    def _fetch():
        _sleep()
        try:
            stats = leaguedashplayerstats.LeagueDashPlayerStats(
                season="2024-25",
                per_mode_simple="PerGame",
            )
            df = stats.get_data_frames()[0]
            result = {}
            for _, row in df.iterrows():
                pid = str(row.get("PLAYER_ID", ""))
                # Sleeper points scoring: PTS + REB*1.2 + AST*1.5 + STL*3 + BLK*3 + TO*-1
                pts = float(row.get("PTS", 0))
                reb = float(row.get("REB", 0))
                ast = float(row.get("AST", 0))
                stl = float(row.get("STL", 0))
                blk = float(row.get("BLK", 0))
                tov = float(row.get("TOV", 0))
                fantasy_pts = pts + (reb * 1.2) + (ast * 1.5) + (stl * 3) + (blk * 3) - (tov * 1)
                result[pid] = {
                    "fantasy_pts": round(fantasy_pts, 1),
                    "pts": round(pts, 1),
                    "reb": round(reb, 1),
                    "ast": round(ast, 1),
                    "gp": int(row.get("GP", 0)),
                    "name": str(row.get("PLAYER_NAME", "")),
                    "team": str(row.get("TEAM_ABBREVIATION", "")),
                }
            return result
        except Exception as e:
            print(f"[player_avgs] Error: {e}")
            return {}

    loop = asyncio.get_event_loop()
    avgs = await loop.run_in_executor(None, _fetch)
    await cache_set("nba:player_avgs", avgs, 7200)
    return avgs

# ---------------------------------------------------------------------------
# Live scoreboard + lineup detection
# ---------------------------------------------------------------------------

async def get_live_scoreboard() -> dict:
    """Today's live scoreboard. Cache for 60s only."""
    cached = await cache_get("nba:live_scoreboard")
    if cached:
        return cached

    def _fetch():
        try:
            board = live_scoreboard.ScoreBoard()
            return board.get_dict()
        except Exception as e:
            print(f"[live_scoreboard] Error: {e}")
            return {}

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, _fetch)
    await cache_set("nba:live_scoreboard", data, TTL_LIVE_SCOREBOARD)
    return data

async def get_game_starters(game_id: str) -> dict:
    """
    Returns confirmed starters for a given game_id from live boxscore.
    Returns {home_starters: [...], away_starters: [...]} with player IDs and names.
    Only available once game has started or officials released lineups.
    """
    cache_key = f"nba:starters:{game_id}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    def _fetch():
        try:
            box = live_boxscore.BoxScore(game_id=game_id)
            data = box.get_dict()
            game = data.get("game", {})
            
            home_starters = []
            away_starters = []
            
            for team_key in ["homeTeam", "awayTeam"]:
                team = game.get(team_key, {})
                players = team.get("players", [])
                starters = [
                    {
                        "player_id": str(p.get("personId", "")),
                        "name": p.get("name", ""),
                        "starter": p.get("starter", "0") == "1",
                        "status": p.get("status", ""),
                    }
                    for p in players
                ]
                if team_key == "homeTeam":
                    home_starters = starters
                else:
                    away_starters = starters
            
            return {"home": home_starters, "away": away_starters}
        except Exception as e:
            print(f"[starters] Error for game {game_id}: {e}")
            return {"home": [], "away": []}

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _fetch)
    # Cache for 2 min — starters don't change mid-game
    await cache_set(cache_key, result, 120)
    return result

async def get_todays_games() -> list[dict]:
    """Return today's game schedule with game_ids, teams, tip-off times."""
    cached = await cache_get("nba:today_games")
    if cached:
        return cached

    board = await get_live_scoreboard()
    games = []
    
    try:
        game_list = board.get("scoreboard", {}).get("games", [])
        for g in game_list:
            games.append({
                "game_id": g.get("gameId", ""),
                "status": g.get("gameStatusText", ""),
                "status_code": g.get("gameStatus", 1),  # 1=scheduled, 2=live, 3=final
                "home_team": g.get("homeTeam", {}).get("teamTricode", ""),
                "away_team": g.get("awayTeam", {}).get("teamTricode", ""),
                "home_score": g.get("homeTeam", {}).get("score", 0),
                "away_score": g.get("awayTeam", {}).get("score", 0),
                "game_time_utc": g.get("gameTimeUTC", ""),
                "game_time_est": g.get("gameEt", ""),
            })
    except Exception as e:
        print(f"[today_games] Parse error: {e}")
    
    await cache_set("nba:today_games", games, 300)  # 5 min
    return games
