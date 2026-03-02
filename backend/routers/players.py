from fastapi import APIRouter, Query
from services.sleeper_api import get_all_nba_players, player_image_url

router = APIRouter(prefix="/players", tags=["players"])

ACTIVE_POSITIONS = {"PG", "SG", "SF", "PF", "C", "G", "F"}
ACTIVE_STATUSES = {"Active", "active"}

@router.get("/search")
async def search_players(q: str = Query("", min_length=0)):
    """
    Search NBA players by name. Returns top 20 matches.
    Used in the manual roster builder UI (card picker).
    """
    all_players = await get_all_nba_players()
    
    query = q.lower().strip()
    results = []
    
    for pid, p in all_players.items():
        # Filter to only NBA players with valid positions
        sport = p.get("sport", "")
        if sport and sport != "nba":
            continue
        
        first = p.get("first_name", "") or ""
        last = p.get("last_name", "") or ""
        full_name = f"{first} {last}".strip()
        
        if not full_name:
            continue
        
        # Filter to active NBA players with positions
        team = p.get("team")
        if not team:  # No team = likely retired/inactive
            continue
        
        # Match query
        if query and query not in full_name.lower():
            continue
        
        position = p.get("position") or (p.get("fantasy_positions") or ["F"])[0]
        
        results.append({
            "player_id": pid,
            "full_name": full_name,
            "first_name": first,
            "last_name": last,
            "team": team or "",
            "position": position,
            "injury_status": p.get("injury_status"),
            "status": p.get("status", "active"),
            "img_url": player_image_url(pid),
            "number": p.get("number", ""),
        })
    
    # Sort: active first, then alphabetical
    results.sort(key=lambda x: (x.get("injury_status") is not None, x["full_name"]))
    
    return results[:50]

@router.get("/sleeper/{player_id}")
async def get_player_detail(player_id: str):
    """Get single player data from Sleeper."""
    all_players = await get_all_nba_players()
    p = all_players.get(player_id)
    if not p:
        return {"error": "Player not found"}
    
    first = p.get("first_name", "") or ""
    last = p.get("last_name", "") or ""
    
    return {
        "player_id": player_id,
        "full_name": f"{first} {last}".strip(),
        "team": p.get("team"),
        "position": p.get("position"),
        "injury_status": p.get("injury_status"),
        "img_url": player_image_url(player_id),
    }
