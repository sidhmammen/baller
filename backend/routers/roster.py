from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from typing import Optional
import uuid

from db import get_db
from models.roster import UserRoster, RosterPlayer
from models.player import Player
from services.sleeper_api import (
    get_sleeper_user,
    get_user_leagues,
    get_league,
    get_league_rosters,
    get_league_users,
    get_all_nba_players,
    player_image_url,
)

from services.nba_data import (
    ensure_team_schedule_cached,
    ensure_team_def_ratings_cached,
    ensure_player_season_averages_cached,
)

router = APIRouter(prefix="/roster", tags=["roster"])

class RosterSetupRequest(BaseModel):
    session_id: Optional[str] = None
    sleeper_username: Optional[str] = None
    sleeper_league_id: Optional[str] = None
    league_size: int = 10
    scoring_type: str = "points_h2h"
    player_ids: list[str] = []  # Sleeper player_id strings

class RosterResponse(BaseModel):
    session_id: str
    league_size: int
    scoring_type: str
    sleeper_username: Optional[str]
    sleeper_league_id: Optional[str]
    players: list[dict]

@router.post("/setup", response_model=RosterResponse)
async def setup_roster(req: RosterSetupRequest, db: AsyncSession = Depends(get_db)):
    """
    Set up a user's fantasy roster.
    Either provide player_ids directly, or provide a sleeper_league_id
    and the backend will fetch the roster from Sleeper's API.
    """
    session_id = req.session_id or str(uuid.uuid4())

    # Fetch Sleeper players list to enrich our player data
    all_sleeper_players = await get_all_nba_players()

    player_ids = req.player_ids

    # If Sleeper username + league provided, auto-fetch their roster
    if req.sleeper_username and req.sleeper_league_id:
        user = await get_sleeper_user(req.sleeper_username)
        if not user:
            raise HTTPException(status_code=404, detail="Sleeper username not found")

        user_id = user.get("user_id")
        rosters = await get_league_rosters(req.sleeper_league_id)
        users = await get_league_users(req.sleeper_league_id)

        # Auto-detect league size from actual roster count
        if len(rosters) > 0:
            req.league_size = len(rosters)
            print(f"[roster] Auto-detected league size: {req.league_size}")

        user_map = {u["user_id"]: u for u in users}
        my_roster = None
        for r in rosters:
            if r.get("owner_id") == user_id:
                my_roster = r
                break

        if not my_roster:
            raise HTTPException(status_code=404, detail="User's roster not found in that league")

        player_ids = my_roster.get("players") or []

    if not player_ids:
        raise HTTPException(status_code=400, detail="No players provided")

    # Upsert UserRoster
    existing = await db.execute(
        select(UserRoster).where(UserRoster.session_id == session_id)
    )
    user_roster = existing.scalar_one_or_none()

    if user_roster:
        user_roster.league_size = req.league_size
        user_roster.scoring_type = req.scoring_type
        user_roster.sleeper_username = req.sleeper_username
        user_roster.sleeper_league_id = req.sleeper_league_id
    else:
        user_roster = UserRoster(
            session_id=session_id,
            league_size=req.league_size,
            scoring_type=req.scoring_type,
            sleeper_username=req.sleeper_username,
            sleeper_league_id=req.sleeper_league_id,
        )
        db.add(user_roster)

    # Clear existing roster players
    await db.execute(delete(RosterPlayer).where(RosterPlayer.session_id == session_id))

    # Upsert players into Players table and create RosterPlayer entries
    enriched_players = []
    for pid in player_ids:
        sleeper_p = all_sleeper_players.get(str(pid), {})
        if not sleeper_p:
            continue

        full_name = f"{sleeper_p.get('first_name', '')} {sleeper_p.get('last_name', '')}".strip()
        if not full_name:
            continue

        # Upsert into players table
        existing_player = await db.execute(select(Player).where(Player.player_id == str(pid)))
        player = existing_player.scalar_one_or_none()

        team = sleeper_p.get("team") or ""
        position = sleeper_p.get("position") or sleeper_p.get("fantasy_positions", ["F"])[0] if sleeper_p.get("fantasy_positions") else "F"

        if player:
            player.full_name = full_name
            player.team = team
            player.position = position
            player.injury_status = sleeper_p.get("injury_status")
            player.status = sleeper_p.get("status", "active")
        else:
            player = Player(
                player_id=str(pid),
                full_name=full_name,
                first_name=sleeper_p.get("first_name", ""),
                last_name=sleeper_p.get("last_name", ""),
                team=team,
                position=position,
                injury_status=sleeper_p.get("injury_status"),
                status=sleeper_p.get("status", "active"),
                sleeper_img_url=player_image_url(str(pid)),
            )
            db.add(player)

        roster_entry = RosterPlayer(session_id=session_id, player_id=str(pid))
        db.add(roster_entry)

        enriched_players.append({
            "player_id": str(pid),
            "full_name": full_name,
            "team": team,
            "position": position,
            "injury_status": sleeper_p.get("injury_status"),
            "img_url": player_image_url(str(pid)),
        })

    await db.commit()

    # TEMP: warm synchronously so schedule isn't blank on first load
    teams = sorted({p["team"] for p in enriched_players if p.get("team")})

    print("[roster] warming nba caches...", flush=True)
    await ensure_player_season_averages_cached(season="2025-26")
    await ensure_team_def_ratings_cached(season="2025-26")
    for team in teams:
        await ensure_team_schedule_cached(team)

    print(f"[roster] warmed caches for {len(teams)} teams", flush=True)

    # Pre-warm NBA cache in background so first schedule load is instant
    async def _prewarm():
        try:
            import asyncio as _asyncio

            teams = sorted({p["team"] for p in enriched_players if p.get("team")})

            await ensure_player_season_averages_cached(season="2025-26")
            await _asyncio.sleep(0.8)

            await ensure_team_def_ratings_cached(season="2025-26")
            await _asyncio.sleep(0.8)

            for team in teams:
                await ensure_team_schedule_cached(team)
                await _asyncio.sleep(0.8)

            print(f"[roster] Cache pre-warmed for {len(teams)} teams", flush=True)
        except Exception as e:
            print(f"[roster] Pre-warm error: {e}", flush=True)

    import asyncio as _asyncio
    _asyncio.create_task(_prewarm())

    return RosterResponse(
        session_id=session_id,
        league_size=req.league_size,
        scoring_type=req.scoring_type,
        sleeper_username=req.sleeper_username,
        sleeper_league_id=req.sleeper_league_id,
        players=enriched_players,
    )

@router.get("/{session_id}", response_model=RosterResponse)
async def get_roster(session_id: str, db: AsyncSession = Depends(get_db)):
    user_roster_q = await db.execute(
        select(UserRoster).where(UserRoster.session_id == session_id)
    )
    user_roster = user_roster_q.scalar_one_or_none()
    if not user_roster:
        raise HTTPException(status_code=404, detail="Roster not found")

    roster_players_q = await db.execute(
        select(RosterPlayer).where(RosterPlayer.session_id == session_id)
    )
    roster_entries = roster_players_q.scalars().all()

    players = []
    for entry in roster_entries:
        p_q = await db.execute(select(Player).where(Player.player_id == entry.player_id))
        p = p_q.scalar_one_or_none()
        if p:
            players.append({
                "player_id": p.player_id,
                "full_name": p.full_name,
                "team": p.team,
                "position": p.position,
                "injury_status": p.injury_status,
                "img_url": p.sleeper_img_url or player_image_url(p.player_id),
            })

@router.delete("/{session_id}/player/{player_id}")
async def remove_player(session_id: str, player_id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(
        delete(RosterPlayer).where(
            RosterPlayer.session_id == session_id,
            RosterPlayer.player_id == player_id,
        )
    )
    await db.commit()
    return {"status": "removed", "player_id": player_id}

