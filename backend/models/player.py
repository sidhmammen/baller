from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime
from sqlalchemy.sql import func
from db import Base

class Player(Base):
    __tablename__ = "players"

    player_id = Column(String, primary_key=True)   # Sleeper player_id (string)
    full_name = Column(String, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    team = Column(String)                          # team abbreviation e.g. "LAL"
    nba_team_id = Column(Integer)
    position = Column(String)                      # PG, SG, SF, PF, C
    status = Column(String, default="active")      # active, injured, etc.
    injury_status = Column(String, nullable=True)  # Q, D, O, etc.
    fantasy_rank = Column(Integer, nullable=True)  # estimated ownership rank
    avg_fantasy_pts = Column(Float, default=0.0)
    sleeper_img_url = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
