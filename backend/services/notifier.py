"""
WebSocket broadcast layer.
The lineup poller publishes to Redis channel "lineup_alerts".
This module subscribes and pushes to all connected WS clients.
"""
import asyncio
import json
from typing import Dict, Set
import redis.asyncio as aioredis
from redis_client import get_redis

# session_id → set of WebSocket connections
_connections: Dict[str, Set] = {}

def register(session_id: str, websocket) -> None:
    _connections.setdefault(session_id, set()).add(websocket)

def unregister(session_id: str, websocket) -> None:
    if session_id in _connections:
        _connections[session_id].discard(websocket)
        if not _connections[session_id]:
            del _connections[session_id]

async def broadcast_to_session(session_id: str, message: dict) -> None:
    """Send a message to all WebSocket connections for a session."""
    sockets = _connections.get(session_id, set()).copy()
    dead = set()
    for ws in sockets:
        try:
            await ws.send_json(message)
        except Exception:
            dead.add(ws)
    for ws in dead:
        unregister(session_id, ws)

async def broadcast_to_all(message: dict) -> None:
    """Broadcast to every connected session (e.g. live game score updates)."""
    for session_id in list(_connections.keys()):
        await broadcast_to_session(session_id, message)

async def start_redis_subscriber():
    """
    Background task that subscribes to Redis 'lineup_alerts' channel
    and routes notifications to the correct WS session.
    """
    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe("lineup_alerts", "score_updates")
    
    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
        try:
            data = json.loads(message["data"])
            session_id = data.get("session_id")
            if session_id:
                await broadcast_to_session(session_id, data)
            else:
                await broadcast_to_all(data)
        except Exception as e:
            print(f"[notifier] Error processing message: {e}")
