from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Enum
from sqlalchemy.sql import func
from db import Base
import enum

class ScoringType(str, enum.Enum):
    points_h2h = "points_h2h"
    categories_h2h = "categories_h2h"
    categories_roto = "categories_roto"

class UserRoster(Base):
    __tablename__ = "user_rosters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False, index=True, unique=True)
    sleeper_username = Column(String, nullable=True)
    sleeper_league_id = Column(String, nullable=True)
    league_size = Column(Integer, default=10)
    scoring_type = Column(String, default="points_h2h")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class RosterPlayer(Base):
    __tablename__ = "roster_players"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False, index=True)
    player_id = Column(String, ForeignKey("players.player_id"), nullable=False)
    slot = Column(String, nullable=True)  # PG, SG, SF, PF, C, G, F, UTIL, BN
    added_at = Column(DateTime(timezone=True), server_default=func.now())
