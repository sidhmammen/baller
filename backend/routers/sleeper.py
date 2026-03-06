from fastapi import APIRouter, HTTPException
from services.sleeper_api import get_sleeper_user, get_user_leagues, get_league, get_league_rosters, get_league_users

router = APIRouter(prefix="/sleeper", tags=["sleeper"])

@router.get("/user/{username}")
async def lookup_user(username: str):
    user = await get_sleeper_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="Sleeper user not found")
    return user

@router.get("/user/{username}/leagues")
async def get_leagues_for_user(username: str, season: str = "2025"):
    user = await get_sleeper_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="Sleeper user not found")
    
    leagues = await get_user_leagues(user["user_id"], season)
    # Filter to NBA leagues only
    nba_leagues = [l for l in leagues if l.get("sport") == "nba"]
    
    return [
        {
            "league_id": l.get("league_id"),
            "name": l.get("name"),
            "total_rosters": l.get("total_rosters"),
            "scoring_settings": l.get("scoring_settings", {}),
            "status": l.get("status"),
            "season": l.get("season"),
        }
        for l in nba_leagues
    ]

@router.get("/league/{league_id}/preview")
async def preview_league(league_id: str):
    """Preview a league before importing — shows all rosters + team names."""
    league = await get_league(league_id)
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    rosters = await get_league_rosters(league_id)
    users = await get_league_users(league_id)
    user_map = {u["user_id"]: u for u in users}
    
    return {
        "league": {
            "name": league.get("name"),
            "total_rosters": league.get("total_rosters"),
            "status": league.get("status"),
        },
        "rosters": [
            {
                "roster_id": r.get("roster_id"),
                "owner_id": r.get("owner_id"),
                "display_name": user_map.get(r.get("owner_id") or "", {}).get("display_name", "Unknown"),
                "player_count": len(r.get("players") or []),
                "players": r.get("players") or [],
            }
            for r in rosters
        ]
    }
