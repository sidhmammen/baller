"""
Sleeper API integration — no auth required for read operations.
Docs: https://docs.sleeper.com/
"""
import httpx
import asyncio
from typing import Optional
from redis_client import cache_get, cache_set, TTL_SLEEPER_PLAYERS

SLEEPER_BASE = "https://api.sleeper.app/v1"
CDN_BASE = "https://sleepercdn.com/content/nfl/players/thumb"
NBA_CDN = "https://sleepercdn.com/content/nba/players"

async def get_sleeper_user(username: str) -> Optional[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SLEEPER_BASE}/user/{username}")
        if resp.status_code == 200:
            return resp.json()
    return None

async def get_user_leagues(user_id: str, season: str = "2024") -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SLEEPER_BASE}/user/{user_id}/leagues/nba/{season}")
        if resp.status_code == 200:
            return resp.json() or []
    return []

async def get_league(league_id: str) -> Optional[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SLEEPER_BASE}/league/{league_id}")
        if resp.status_code == 200:
            return resp.json()
    return None

async def get_league_rosters(league_id: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SLEEPER_BASE}/league/{league_id}/rosters")
        if resp.status_code == 200:
            return resp.json() or []
    return []

async def get_league_users(league_id: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SLEEPER_BASE}/league/{league_id}/users")
        if resp.status_code == 200:
            return resp.json() or []
    return []

async def get_all_nba_players() -> dict:
    """
    Returns all NBA players from Sleeper. This is a large payload (~50k+ entries)
    but contains player_id, name, team, position, injury status.
    Cache for 24 hours.
    """
    cached = await cache_get("sleeper:all_players")
    if cached:
        return cached

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{SLEEPER_BASE}/players/nba")
        if resp.status_code == 200:
            players = resp.json()
            await cache_set("sleeper:all_players", players, TTL_SLEEPER_PLAYERS)
            return players
    return {}

async def get_trending_players(sport: str = "nba", trend_type: str = "add", limit: int = 50) -> list[dict]:
    """Returns trending adds/drops on Sleeper — useful for waiver wire context."""
    cached = await cache_get(f"sleeper:trending:{sport}:{trend_type}")
    if cached:
        return cached

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SLEEPER_BASE}/players/{sport}/trending/{trend_type}",
            params={"lookback_hours": 24, "limit": limit}
        )
        if resp.status_code == 200:
            data = resp.json() or []
            await cache_set(f"sleeper:trending:{sport}:{trend_type}", data, 1800)  # 30 min
            return data
    return []

def player_image_url(player_id: str) -> str:
    """Sleeper CDN URL for player headshot thumbnails."""
    return f"https://sleepercdn.com/content/nba/players/thumb/{player_id}.jpg"
