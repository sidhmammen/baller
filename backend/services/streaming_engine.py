"""
Core streaming logic — computes stream scores for roster players
and waiver wire targets.

Stream Score Formula (visible to user in UI):
  score = (games_this_week × 3)
        + (avg_fantasy_pts × 1.5)
        - (back_to_back_count × 2)
        + (schedule_bonus)            # +3 if facing bottom-10 defense
        - (injury_penalty)            # -5 if questionable

Each component is returned separately so the UI can show the breakdown.
"""
from datetime import datetime, timedelta
import pytz
from typing import Optional
from services.nba_data import (
    get_team_schedule_this_week,
    get_team_def_ratings,
    get_player_season_averages,
)

EASTERN = pytz.timezone("America/New_York")

GAMES_PER_WEEK_WEIGHT = 3.0
AVG_PTS_WEIGHT = 1.5
BACK_TO_BACK_PENALTY = 2.0
TOUGH_DEF_PENALTY = -2.0    # facing top-10 defense
SOFT_DEF_BONUS = 3.0        # facing bottom-10 defense
INJURY_Q_PENALTY = 5.0
INJURY_O_PENALTY = 10.0

async def compute_player_week(
    player_id: str,
    player_name: str,
    team_abbr: str,
    position: str,
    avg_fantasy_pts: float,
    injury_status: Optional[str],
    nba_player_id: Optional[str] = None,
) -> dict:
    """
    Returns full week breakdown + stream score for a single player.
    """
    def_ratings = await get_team_def_ratings()
    games = await get_team_schedule_this_week(team_abbr)

    # Detect back-to-backs
    game_dates = []
    for g in games:
        try:
            dt = datetime.strptime(g["game_date"], "%Y-%m-%d").date()
            game_dates.append(dt)
        except Exception:
            pass
    game_dates.sort()

    back_to_back_count = 0
    back_to_back_dates = set()
    for i in range(1, len(game_dates)):
        if (game_dates[i] - game_dates[i - 1]).days == 1:
            back_to_back_count += 1
            back_to_back_dates.add(game_dates[i])
            back_to_back_dates.add(game_dates[i - 1])

    # Enrich games with defense info
    enriched_games = []
    schedule_bonus = 0.0
    for g in games:
        opp = g.get("opponent", "")
        opp_def = def_ratings.get(opp, {})
        def_rank = opp_def.get("def_rank", 15)
        opp_pts = opp_def.get("opp_pts", 110.0)

        try:
            gdate = datetime.strptime(g["game_date"], "%Y-%m-%d").date()
            is_b2b = gdate in back_to_back_dates
        except Exception:
            is_b2b = False

        # Bonus/penalty per game
        if def_rank >= 21:  # bottom-10 defense
            schedule_bonus += SOFT_DEF_BONUS
            matchup_grade = "A"
        elif def_rank <= 10:  # top-10 defense
            schedule_bonus += TOUGH_DEF_PENALTY
            matchup_grade = "C"
        else:
            matchup_grade = "B"

        enriched_games.append({
            **g,
            "is_back_to_back": is_b2b,
            "opp_def_rank": def_rank,
            "opp_pts_allowed": opp_pts,
            "matchup_grade": matchup_grade,
        })

    # Injury penalty
    injury_penalty = 0.0
    if injury_status in ("Q", "GTD"):
        injury_penalty = INJURY_Q_PENALTY
    elif injury_status in ("O", "IR", "INJ"):
        injury_penalty = INJURY_O_PENALTY

    games_count = len(games)
    score = (
        (games_count * GAMES_PER_WEEK_WEIGHT)
        + (avg_fantasy_pts * AVG_PTS_WEIGHT)
        - (back_to_back_count * BACK_TO_BACK_PENALTY)
        + schedule_bonus
        - injury_penalty
    )

    return {
        "player_id": player_id,
        "player_name": player_name,
        "team": team_abbr,
        "position": position,
        "avg_fantasy_pts": avg_fantasy_pts,
        "injury_status": injury_status,
        "games_this_week": games_count,
        "schedule": enriched_games,
        "back_to_back_count": back_to_back_count,
        "stream_score": round(score, 1),
        "score_breakdown": {
            "games_component": round(games_count * GAMES_PER_WEEK_WEIGHT, 1),
            "avg_pts_component": round(avg_fantasy_pts * AVG_PTS_WEIGHT, 1),
            "b2b_penalty": round(-back_to_back_count * BACK_TO_BACK_PENALTY, 1),
            "schedule_bonus": round(schedule_bonus, 1),
            "injury_penalty": round(-injury_penalty, 1),
        },
        "stream_recommendation": _grade(score, games_count, injury_status),
    }

def _grade(score: float, games: int, injury: Optional[str]) -> str:
    if injury in ("O", "IR"):
        return "OUT"
    if injury in ("Q", "GTD"):
        return "QUESTIONABLE"
    if score >= 55:
        return "MUST_PLAY"
    if score >= 40:
        return "STREAM"
    if score >= 25:
        return "SIT"
    return "DROP"

async def get_waiver_targets(
    league_size: int,
    roster_player_ids: list[str],
    limit: int = 20,
) -> list[dict]:
    """
    Returns top streamable players not on the user's roster,
    estimated to be available based on league size.
    
    Ownership thresholds (approximate roster spots):
      6 teams  × 13 spots = ~78 players owned
      8 teams  × 13 spots = ~104 players owned
      10 teams × 13 spots = ~130 players owned
      12 teams × 13 spots = ~156 players owned
      14 teams × 13 spots = ~182 players owned
    """
    ownership_cutoff = {6: 78, 8: 104, 10: 130, 12: 156, 14: 182}
    cutoff = ownership_cutoff.get(league_size, 130)

    avgs = await get_player_season_averages()
    def_ratings = await get_team_def_ratings()

    # Sort all players by fantasy pts, take those outside ownership threshold
    sorted_players = sorted(avgs.items(), key=lambda x: x[1]["fantasy_pts"], reverse=True)
    
    # Players ranked beyond cutoff are likely available
    available_players = sorted_players[cutoff:]
    
    # Also ensure they're not on the user's roster
    # Note: nba_api uses numeric player IDs, Sleeper uses string IDs
    # We store the Sleeper IDs in roster, but nba_api IDs are different.
    # We match by name as a bridge (handled in the router layer).
    
    targets = []
    for rank, (nba_pid, stats) in enumerate(available_players[:limit * 2], start=cutoff + 1):
        team = stats.get("team", "")
        games = await get_team_schedule_this_week(team)
        games_count = len(games)
        
        if games_count == 0:
            continue

        # Compute simple schedule bonus
        schedule_bonus = 0.0
        for g in games:
            opp = g.get("opponent", "")
            def_rank = def_ratings.get(opp, {}).get("def_rank", 15)
            if def_rank >= 21:
                schedule_bonus += SOFT_DEF_BONUS
            elif def_rank <= 10:
                schedule_bonus += TOUGH_DEF_PENALTY

        fp = stats.get("fantasy_pts", 0)
        score = (games_count * GAMES_PER_WEEK_WEIGHT) + (fp * AVG_PTS_WEIGHT) + schedule_bonus

        targets.append({
            "nba_player_id": nba_pid,
            "player_name": stats.get("name", ""),
            "team": team,
            "avg_fantasy_pts": fp,
            "games_this_week": games_count,
            "stream_score": round(score, 1),
            "estimated_rank": rank,
            "likely_available": True,
            "score_breakdown": {
                "games_component": round(games_count * GAMES_PER_WEEK_WEIGHT, 1),
                "avg_pts_component": round(fp * AVG_PTS_WEIGHT, 1),
                "schedule_bonus": round(schedule_bonus, 1),
            },
        })

        if len(targets) >= limit:
            break

    targets.sort(key=lambda x: x["stream_score"], reverse=True)
    return targets
