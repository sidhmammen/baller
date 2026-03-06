from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import json

from db import get_db
from models.notification import Notification
from services import notifier
from services.nba_data import get_todays_games

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    notifier.register(session_id, websocket)

    # Send today's games immediately on connect
    try:
        games = await get_todays_games()
        await websocket.send_json({"type": "today_games", "games": games})
    except Exception:
        pass

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except Exception:
                pass
    except WebSocketDisconnect:
        notifier.unregister(session_id, websocket)
    except RuntimeError:
        # Client disconnected abruptly without a clean close frame
        notifier.unregister(session_id, websocket)
    except Exception:
        notifier.unregister(session_id, websocket)

@router.get("/{session_id}")
async def get_notifications(session_id: str, db: AsyncSession = Depends(get_db)):
    """Return all notifications for a session, most recent first."""
    result = await db.execute(
        select(Notification)
        .where(Notification.session_id == session_id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    notifications = result.scalars().all()
    return [
        {
            "id": n.id,
            "player_id": n.player_id,
            "player_name": n.player_name,
            "notification_type": n.notification_type,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifications
    ]

@router.post("/{session_id}/read-all")
async def mark_all_read(session_id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(
        update(Notification)
        .where(Notification.session_id == session_id, Notification.is_read == False)
        .values(is_read=True)
    )
    await db.commit()
    return {"status": "ok"}

@router.get("/games/today")
async def today_games():
    """Live scoreboard — today's NBA games with scores."""
    games = await get_todays_games()
    return {"games": games}
