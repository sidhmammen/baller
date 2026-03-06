from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from db import init_db
from routers import roster, players, schedule, notifications, sleeper
from services.notifier import start_redis_subscriber
from services.lineup_poller import init_scheduler

app = FastAPI(
    title="Fantasy NBA Streaming Assistant",
    description="Daily streaming decisions and pre-game lineup alerts for Sleeper fantasy basketball.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(roster.router)
app.include_router(players.router)
app.include_router(schedule.router)
app.include_router(notifications.router)
app.include_router(sleeper.router)


from services.notifier import start_redis_subscriber, start_score_broadcaster

@app.on_event("startup")
async def startup():
    await init_db()
    asyncio.create_task(start_redis_subscriber())
    asyncio.create_task(start_score_broadcaster())  # ← add this line
    init_scheduler()
    print("🏀 Fantasy NBA API started")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "fantasy-nba-api"}


@app.get("/")
async def root():
    return {
        "message": "Fantasy NBA Streaming Assistant API",
        "docs": "/docs",
        "health": "/health",
    }