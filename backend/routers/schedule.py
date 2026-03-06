from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import pytz

from db import get_db
from models.roster import UserRoster, RosterPlayer
from models.player import Player

from services.streaming_engine import compute_player_week
from services.nba_data import (
    get_player_season_averages_cached,
    get_player_name_map_cached,
    normalize_player_name,
)

router = APIRouter(prefix="/schedule", tags=["schedule"])
EASTERN = pytz.timezone("America/New_York")

def _week_key_et() -> str:
    today = datetime.now(EASTERN).date()
    monday = today - timedelta(days=today.weekday())
    return monday.strftime("%Y-%m-%d")

@router.get("/{session_id}")
async def get_weekly_schedule(session_id: str, db: AsyncSession = Depends(get_db)):
    user_roster_q = await db.execute(select(UserRoster).where(UserRoster.session_id == session_id))
    user_roster = user_roster_q.scalar_one_or_none()
    if not user_roster:
        raise HTTPException(status_code=404, detail="Roster not found")

    roster_q = await db.execute(select(RosterPlayer).where(RosterPlayer.session_id == session_id))
    roster_entries = roster_q.scalars().all()

    nba_avgs = await get_player_season_averages_cached()
    name_map = await get_player_name_map_cached()

    week_key = _week_key_et()

    results = []
    for entry in roster_entries:
        p_q = await db.execute(select(Player).where(Player.player_id == entry.player_id))
        p = p_q.scalar_one_or_none()
        if not p or not p.team:
            continue

        avg_fantasy_pts = 0.0
        nba_pid = None

        nm = normalize_player_name(p.full_name or "")
        nba_pid = name_map.get(nm)
        if nba_pid and nba_pid in nba_avgs:
            avg_fantasy_pts = float(nba_avgs[nba_pid].get("fantasy_pts", 0.0) or 0.0)

        week_data = await compute_player_week(
            player_id=p.player_id,
            player_name=p.full_name,
            team_abbr=p.team,
            position=p.position or "F",
            avg_fantasy_pts=avg_fantasy_pts,
            injury_status=p.injury_status,
            week_key=week_key,
        )

        week_data["img_url"] = p.sleeper_img_url or f"https://sleepercdn.com/content/nba/players/thumb/{p.player_id}.jpg"
        results.append(week_data)

    results.sort(key=lambda x: x.get("stream_score", 0), reverse=True)

    return {
        "session_id": session_id,
        "league_size": user_roster.league_size,
        "scoring_type": user_roster.scoring_type,
        "week_key": week_key,
        "players": results,
    }