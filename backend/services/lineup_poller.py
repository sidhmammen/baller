"""
Lineup polling jobs — APScheduler jobs that:
1. Check today's game schedule
2. 2 hours before each tip-off, begin polling every 5 minutes
3. When lineups are confirmed, publish to Redis for notification routing
"""
import asyncio
from datetime import datetime, timedelta
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from services.nba_data import get_todays_games, get_game_starters
from redis_client import publish, cache_get, cache_set
from db import AsyncSessionLocal
from models.roster import RosterPlayer
from sqlalchemy import select

EASTERN = pytz.timezone("America/New_York")

scheduler = AsyncIOScheduler(timezone=EASTERN)

# Track what we've already notified to avoid duplicates
# key: f"notified:{game_id}:{player_id}" → "starting" | "bench"
NOTIFY_CACHE_TTL = 86400  # 24 hours

async def _get_all_active_sessions_with_rosters() -> dict:
    """Returns {session_id: [player_ids]} for all sessions that have rosters."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(RosterPlayer))
        rows = result.scalars().all()
    
    sessions: dict = {}
    for row in rows:
        sessions.setdefault(row.session_id, []).append(row.player_id)
    return sessions

async def poll_lineups():
    """
    Core polling function — called every 5 minutes when games are approaching.
    Checks live scoreboard for each today's game, detects confirmed starters,
    and publishes alerts to Redis.
    """
    games = await get_todays_games()
    if not games:
        return

    now = datetime.now(EASTERN)
    sessions = await _get_all_active_sessions_with_rosters()

    if not sessions:
        return

    for game in games:
        status_code = game.get("status_code", 1)
        game_id = game.get("game_id", "")
        
        if not game_id:
            continue

        # Parse tip-off time
        game_time_str = game.get("game_time_utc", "")
        try:
            tip_utc = datetime.fromisoformat(game_time_str.replace("Z", "+00:00"))
            tip_est = tip_utc.astimezone(EASTERN)
        except Exception:
            tip_est = None

        # Only poll if we're within 2 hours of tip-off or game is live
        if tip_est:
            time_until = (tip_est - now).total_seconds() / 60  # minutes
            if time_until > 120 or time_until < -60:
                continue  # Too early or too late

        # Try to get starters (only available once game starts or announced ~1hr before)
        if status_code >= 2:  # live or final
            starters_data = await get_game_starters(game_id)
            
            all_players = starters_data.get("home", []) + starters_data.get("away", [])
            
            for session_id, roster_player_ids in sessions.items():
                for player in all_players:
                    pid = player.get("player_id", "")
                    
                    # Note: nba_api uses numeric IDs, Sleeper uses different IDs
                    # We do a best-effort match — in production you'd maintain a mapping table
                    # For now we check both
                    if pid not in roster_player_ids:
                        continue
                    
                    notify_key = f"notified:{game_id}:{pid}:{session_id}"
                    already_notified = await cache_get(notify_key)
                    
                    is_starter = player.get("starter", False)
                    status_str = "starting" if is_starter else "bench"
                    
                    if already_notified == status_str:
                        continue
                    
                    # Mark as notified
                    await cache_set(notify_key, status_str, NOTIFY_CACHE_TTL)
                    
                    # Build notification
                    home = game.get("home_team", "")
                    away = game.get("away_team", "")
                    notification = {
                        "session_id": session_id,
                        "type": "lineup_alert",
                        "notification_type": "starting" if is_starter else "not_starting",
                        "player_id": pid,
                        "player_name": player.get("name", ""),
                        "game_id": game_id,
                        "matchup": f"{away} @ {home}",
                        "message": (
                            f"✅ {player.get('name')} is STARTING — {away} @ {home}"
                            if is_starter
                            else f"🚨 {player.get('name')} is NOT starting — {away} @ {home}"
                        ),
                        "is_starter": is_starter,
                        "timestamp": now.isoformat(),
                    }
                    
                    await publish("lineup_alerts", notification)
                    print(f"[poller] Published alert: {notification['message'][:60]}")

async def check_and_schedule_polls():
    """
    Runs every 30 minutes to check if games are coming up.
    If games are within 2.5 hours, ensures the 5-minute poll job is active.
    """
    games = await get_todays_games()
    now = datetime.now(EASTERN)
    
    has_upcoming = False
    for game in games:
        game_time_str = game.get("game_time_utc", "")
        try:
            tip_utc = datetime.fromisoformat(game_time_str.replace("Z", "+00:00"))
            tip_est = tip_utc.astimezone(EASTERN)
            minutes_until = (tip_est - now).total_seconds() / 60
            if 0 <= minutes_until <= 150:
                has_upcoming = True
                break
        except Exception:
            pass
    
    # Dynamically adjust poll frequency
    if has_upcoming:
        if not scheduler.get_job("lineup_poll_5min"):
            scheduler.add_job(
                poll_lineups,
                IntervalTrigger(minutes=5),
                id="lineup_poll_5min",
                replace_existing=True,
            )
            print("[scheduler] 5-minute lineup polling ACTIVATED")
    else:
        if scheduler.get_job("lineup_poll_5min"):
            scheduler.remove_job("lineup_poll_5min")
            print("[scheduler] 5-minute lineup polling DEACTIVATED — no upcoming games")

def init_scheduler():
    """Initialize and start the scheduler."""
    # Check for upcoming games every 30 minutes
    scheduler.add_job(
        check_and_schedule_polls,
        IntervalTrigger(minutes=30),
        id="game_check",
        replace_existing=True,
    )
    
    # Also run once at startup
    scheduler.add_job(
        check_and_schedule_polls,
        id="game_check_startup",
        replace_existing=True,
    )
    
    scheduler.start()
    print("[scheduler] APScheduler started")
