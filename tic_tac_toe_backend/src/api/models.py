from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import enum

Base = declarative_base()

class GameStatus(str, enum.Enum):
    waiting = "waiting"
    in_progress = "in_progress"
    finished = "finished"

# PUBLIC_INTERFACE
class User(Base):
    """SQLAlchemy model for user accounts."""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    games1 = relationship("Game", foreign_keys="[Game.user1_id]", back_populates="user1")
    games2 = relationship("Game", foreign_keys="[Game.user2_id]", back_populates="user2")
    moves = relationship("Move", back_populates="user")

# PUBLIC_INTERFACE
class Game(Base):
    """SQLAlchemy model for a tic tac toe game between two users."""
    __tablename__ = "games"
    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(Integer, ForeignKey("users.id"))
    user2_id = Column(Integer, ForeignKey("users.id"))
    status = Column(Enum(GameStatus), default=GameStatus.waiting)
    created_at = Column(DateTime, default=datetime.utcnow)
    winner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    user1 = relationship("User", foreign_keys=[user1_id], back_populates="games1")
    user2 = relationship("User", foreign_keys=[user2_id], back_populates="games2")
    moves = relationship("Move", back_populates="game")

# PUBLIC_INTERFACE
class Move(Base):
    """SQLAlchemy model representing a move in a tic tac toe game."""
    __tablename__ = "moves"
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    row = Column(Integer, nullable=False)
    col = Column(Integer, nullable=False)
    move_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    game = relationship("Game", back_populates="moves")
    user = relationship("User", back_populates="moves")
