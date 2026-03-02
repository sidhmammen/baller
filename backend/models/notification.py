from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.sql import func
from db import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False, index=True)
    player_id = Column(String, nullable=False)
    player_name = Column(String, nullable=False)
    game_id = Column(String, nullable=True)
    notification_type = Column(String, nullable=False)  # "starting", "not_starting", "game_start"
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
