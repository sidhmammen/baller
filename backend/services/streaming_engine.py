"""
Streaming engine — cache-only.

This must stay non-blocking for /schedule:
- Pull schedules from Redis (schedule:week2:TEAM:MONDAY)
- Pull def ratings from Redis (nba:def_ratings)
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Dict
import pytz

from services.nba_data import (
    get_player_season_averages_cached,
    get_team_schedule_cached,
    get_team_def_ratings_cached,
    normalize_player_name,
)

EASTERN = pytz.timezone("America/New_York")

# -------------------------
# Scoring config (tweakable)
# -------------------------
GAMES_WEIGHT = 3.0
AVG_PTS_WEIGHT = 1.5        # keep name used in your codebase
B2B_BONUS = 1.5             # keep name used in your codebase
SOFT_DEF_BONUS = 3.0        # opponent def_rank >= 22
TOUGH_DEF_PENALTY = 2.0     # opponent def_rank <= 8

# Optional extra bonuses used by your current file
EFFICIENCY_MAX = 4.0
DURABILITY_MAX = 3.0


def compute_efficiency_bonus(avg_fantasy_pts: float, avg_minutes: float) -> float:
    """
    Small bump for players producing well per minute.
    Stable and bounded so it doesn't dominate the main formula.
    """
    if avg_minutes <= 0:
        return 0.0
    per_min = avg_fantasy_pts / avg_minutes
    # Typical fantasy pts/min ranges ~0.6-1.3; scale into 0..EFFICIENCY_MAX
    bonus = (per_min - 0.75) * 10.0
    return max(0.0, min(EFFICIENCY_MAX, bonus))


def compute_durability_bonus(games_played: int) -> float:
    """
    Small bump for players who have actually played games (reduces risk).
    """
    if games_played <= 0:
        return 0.0
    if games_played >= 60:
        return DURABILITY_MAX
    return (games_played / 60.0) * DURABILITY_MAX


def _injury_penalty(status: Optional[str]) -> float:
    s = (status or "").upper()
    if "OUT" in s:
        return 10.0
    if "GTD" in s or "QUESTION" in s:
        return 5.0
    return 0.0


def _recommendation(score: float, injury_status: Optional[str]) -> str:
    s = (injury_status or "").upper()
    if "OUT" in s:
        return "OUT"
    if "GTD" in s or "QUESTION" in s:
        return "QUESTIONABLE"
    if score >= 55:
        return "MUST_PLAY"
    if score >= 40:
        return "STREAM"
    if score >= 25:
        return "SIT"
    return "DROP"


def _b2b_count(game_dates: List[str]) -> int:
    """
    game_dates are YYYY-MM-DD strings.
    Returns number of back-to-back *occurrences*.
    """
    parsed = []
    for s in game_dates:
        try:
            parsed.append(datetime.strptime(s, "%Y-%m-%d").date())
        except Exception:
            pass
    parsed.sort()
    b2b = 0
    for i in range(1, len(parsed)):
        if (parsed[i] - parsed[i - 1]).days == 1:
            b2b += 1
    return b2b


async def compute_player_week(
    player_id: str,
    player_name: str,
    team_abbr: str,
    position: str,
    avg_fantasy_pts: float,
    injury_status: Optional[str],
    week_key: Optional[str] = None,
) -> dict:
    """
    Cache-only: reads schedule + def ratings from Redis.
    """
    def_ratings = await get_team_def_ratings_cached()
    games = await get_team_schedule_cached(team_abbr, week_key=week_key)

    # b2b
    game_dates = [g.get("game_date", "") for g in games if g.get("game_date")]
    b2b_count = _b2b_count(game_dates)

    schedule_bonus = 0.0
    enriched: List[Dict] = []
    for g in games:
        opp = g.get("opponent", "")
        def_rank = int(def_ratings.get(opp, {}).get("def_rank", 15))

        if def_rank >= 22:
            schedule_bonus += SOFT_DEF_BONUS
            grade = "A"
        elif def_rank <= 8:
            schedule_bonus -= TOUGH_DEF_PENALTY
            grade = "C"
        else:
            grade = "B"

        gg = dict(g)
        gg["matchup_grade"] = grade
        # basic b2b tagging (optional)
        gg["is_back_to_back"] = False
        enriched.append(gg)

    injury_pen = _injury_penalty(injury_status)
    games_count = len(games)

    # Optional enhancements (won't break if you don't have mins/gp)
    avg_minutes = 0.0
    games_played = 0
    # schedule.py can optionally add these if desired

    efficiency_bonus = compute_efficiency_bonus(avg_fantasy_pts, avg_minutes)
    durability_bonus = compute_durability_bonus(games_played)

    score = (
        (games_count * GAMES_WEIGHT)
        + (avg_fantasy_pts * AVG_PTS_WEIGHT)
        + (b2b_count * B2B_BONUS)
        + schedule_bonus
        + efficiency_bonus
        + durability_bonus
        - injury_pen
    )

    return {
        "player_id": player_id,
        "player_name": player_name,
        "team": team_abbr,
        "position": position,
        "avg_fantasy_pts": avg_fantasy_pts,
        "games_this_week": games_count,
        "b2b_count": b2b_count,
        "schedule_bonus": round(schedule_bonus, 1),
        "injury_penalty": injury_pen,
        "stream_score": round(score, 1),
        "recommendation": _recommendation(score, injury_status),
        "schedule": enriched,
    }

async def get_waiver_targets(
    league_size: int,
    owned_names: set,
    limit: int = 20,
) -> list[dict]:
    avgs = await get_player_season_averages_cached()
    def_ratings = await get_team_def_ratings_cached()
    if not avgs:
        return []

    # Pre-fetch unique team schedules (cache-only)
    unique_teams = list({s.get("team", "") for s in avgs.values() if s.get("team")})
    team_schedules = {}
    for team in unique_teams:
        team_schedules[team] = await get_team_schedule_cached(team)

    targets = []
    sorted_players = sorted(avgs.items(), key=lambda x: x[1].get("fantasy_pts", 0), reverse=True)

    for nba_pid, stats in sorted_players:
        player_name = stats.get("name", "")
        if not player_name:
            continue

        # Skip anyone owned in the league (real data)
        if normalize_player_name(player_name) in owned_names:
            continue

        team = stats.get("team", "")
        if not team:
            continue

        games = team_schedules.get(team, [])
        games_count = len(games)
        if games_count == 0:
            continue

        # Detect B2Bs
        game_dates = []
        for g in games:
            try:
                game_dates.append(datetime.strptime(g["game_date"], "%Y-%m-%d").date())
            except Exception:
                pass
        game_dates.sort()
        b2b_count = sum(
            1 for i in range(1, len(game_dates))
            if (game_dates[i] - game_dates[i - 1]).days == 1
        )

        schedule_bonus = 0.0
        for g in games:
            opp = g.get("opponent", "")
            def_rank = def_ratings.get(opp, {}).get("def_rank", 15)
            if def_rank >= 21:
                schedule_bonus += SOFT_DEF_BONUS