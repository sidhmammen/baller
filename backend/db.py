from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://fantasy:fantasy123@localhost:5432/fantasy_nba")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    from models.player import Player
    from models.roster import UserRoster, RosterPlayer
    from models.notification import Notification
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
