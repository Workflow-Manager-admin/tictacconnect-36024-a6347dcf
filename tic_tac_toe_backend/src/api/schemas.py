from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Literal
from datetime import datetime

# ---- User Schemas ----

class UserBase(BaseModel):
    username: str = Field(..., description="Unique username of the user")
    email: EmailStr = Field(..., description="User's email address")

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Password for the user")

class UserLogin(BaseModel):
    username: str
    password: str

class UserRead(UserBase):
    id: int

    class Config:
        orm_mode = True

# ---- Token Schemas ----

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    id: Optional[int]
    username: Optional[str] = None

# ---- Game Schemas ----

class GameBase(BaseModel):
    id: int
    user1_id: int
    user2_id: Optional[int]
    status: Literal["waiting", "in_progress", "finished"]
    created_at: datetime
    winner_id: Optional[int] = None

    class Config:
        orm_mode = True

class GameCreate(BaseModel):
    opponent_username: Optional[str] = Field(None, description="Opponent's username if challenging specific user")
    # If not set, backend pairs with first available user or waits

class GameRead(GameBase):
    pass

# ---- Move Schemas ----

class MoveBase(BaseModel):
    id: int
    game_id: int
    user_id: int
    row: int
    col: int
    move_number: int
    created_at: datetime

    class Config:
        orm_mode = True

class MoveCreate(BaseModel):
    game_id: int
    row: int = Field(..., ge=0, le=2, description="Row index (0-2)")
    col: int = Field(..., ge=0, le=2, description="Column index (0-2)")

class MoveRead(MoveBase):
    pass

# ---- Game + Moves ----

class GameDetail(GameBase):
    moves: List[MoveRead] = []


# ---- History/Overview Schemas ----

class GameSummary(BaseModel):
    id: int
    opponent: str
    status: Literal["waiting", "in_progress", "finished"]
    created_at: datetime
    winner: Optional[str]

class UserHistory(BaseModel):
    games: List[GameSummary]

