from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db import get_db
from models.roster import UserRoster, RosterPlayer
from models.player import Player
from services.streaming_engine import compute_player_week, get_waiver_targets
from services.nba_data import get_player_season_averages
from services.sleeper_api import get_trending_players

router = APIRouter(prefix="/schedule", tags=["schedule"])

@router.get("/{session_id}")
async def get_weekly_schedule(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns weekly schedule + stream score for every player on the user's roster.
    This is the main data source for the Dashboard.
    """
    user_roster_q = await db.execute(
        select(UserRoster).where(UserRoster.session_id == session_id)
    )
    user_roster = user_roster_q.scalar_one_or_none()
    if not user_roster:
        raise HTTPException(status_code=404, detail="Roster not found")
    
    roster_q = await db.execute(
        select(RosterPlayer).where(RosterPlayer.session_id == session_id)
    )
    roster_entries = roster_q.scalars().all()
    
    # Get NBA season averages for fantasy pts
    nba_avgs = await get_player_season_averages()
    
    results = []
    for entry in roster_entries:
        p_q = await db.execute(select(Player).where(Player.player_id == entry.player_id))
        p = p_q.scalar_one_or_none()
        if not p or not p.team:
            continue
        
        # Try to match Sleeper player to NBA stats by name
        avg_fantasy_pts = 0.0
        nba_pid = None
        for npid, stats in nba_avgs.items():
            if stats.get("name", "").lower() == p.full_name.lower():
                avg_fantasy_pts = stats.get("fantasy_pts", 0.0)
                nba_pid = npid
                break
        
        week_data = await compute_player_week(
            player_id=p.player_id,
            player_name=p.full_name,
            team_abbr=p.team,
            position=p.position or "F",
            avg_fantasy_pts=avg_fantasy_pts,
            injury_status=p.injury_status,
            nba_player_id=nba_pid,
        )
        
        week_data["img_url"] = p.sleeper_img_url or f"https://sleepercdn.com/content/nba/players/thumb/{p.player_id}.jpg"
        results.append(week_data)
    
    # Sort by stream_score descending
    results.sort(key=lambda x: x.get("stream_score", 0), reverse=True)
    
    return {
        "session_id": session_id,
        "league_size": user_roster.league_size,
        "scoring_type": user_roster.scoring_type,
        "players": results,
    }

@router.get("/{session_id}/waiver")
async def get_waiver_suggestions(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns top streamable waiver wire targets for this session's league size.
    """
    user_roster_q = await db.execute(
        select(UserRoster).where(UserRoster.session_id == session_id)
    )
    user_roster = user_roster_q.scalar_one_or_none()
    if not user_roster:
        raise HTTPException(status_code=404, detail="Roster not found")
    
    # Get current roster player IDs
    roster_q = await db.execute(
        select(RosterPlayer).where(RosterPlayer.session_id == session_id)
    )
    roster_ids = [r.player_id for r in roster_q.scalars().all()]
    
    targets = await get_waiver_targets(
        league_size=user_roster.league_size,
        roster_player_ids=roster_ids,
        limit=20,
    )
    
    # Enrich with Sleeper trending data
    trending = await get_trending_players(sport="nba", trend_type="add")
    trending_ids = {t.get("player_id"): t.get("count", 0) for t in trending}
    
    for t in targets:
        t["trending_adds"] = trending_ids.get(t.get("nba_player_id"), 0)
    
    return {
        "session_id": session_id,
        "league_size": user_roster.league_size,
        "ownership_cutoff": {6: 78, 8: 104, 10: 130, 12: 156, 14: 182}.get(user_roster.league_size, 130),
        "targets": targets,
    }
