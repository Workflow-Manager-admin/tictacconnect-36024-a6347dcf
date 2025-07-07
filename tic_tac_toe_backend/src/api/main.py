from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta

from .models import Base, User, Game, Move, GameStatus
from .database import engine, get_db
from .schemas import (
    UserCreate, UserRead,
    Token, TokenData,
    GameCreate, GameRead, GameDetail,
    MoveCreate, MoveRead,
    UserHistory, GameSummary,
)
from .game_logic import (
    InvalidMove, NotPlayersTurn, CellOccupied,
    create_board_from_moves,
    check_winner,
    validate_and_get_next_player,
    is_cell_empty,
    is_board_full,
)
import os

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "verysecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

app = FastAPI(
    title="Tic Tac Toe Backend API",
    description="Handles user, game logic, and moves for the fullstack tic tac toe game.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    """
    Creates all database tables for the application if they don't exist.
    Uses SQLAlchemy metadata for automatic table management.
    Called once at FastAPI app startup.
    """
    Base.metadata.create_all(bind=engine)

# --- Auth Helpers ---

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# PUBLIC_INTERFACE
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Dependency to get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user

@app.get("/")
def health_check():
    """Health check endpoint to verify backend is running."""
    return {"message": "Healthy"}

# --- User Registration ---

# PUBLIC_INTERFACE
@app.post("/register", response_model=UserRead, summary="User Registration", tags=["Auth"])
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Registers a new user. Username and email must be unique.
    """
    if db.query(User).filter((User.username == user_in.username) | (User.email == user_in.email)).first():
        raise HTTPException(status_code=400, detail="Username or email already registered")
    hashed_pw = get_password_hash(user_in.password)
    user = User(username=user_in.username, email=user_in.email, hashed_password=hashed_pw)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# --- User Login (JWT) ---

# PUBLIC_INTERFACE
@app.post("/login", response_model=Token, summary="Login to obtain access token", tags=["Auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Authenticates user via username and password.
    Returns JWT token for use in Authorization header.
    """
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.username, "id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

# --- Authenticated User Me ---

# PUBLIC_INTERFACE
@app.get("/users/me", response_model=UserRead, summary="Current user info", tags=["User"])
def read_me(current_user: User = Depends(get_current_user)):
    """
    Returns the currently authenticated user.
    """
    return current_user

# --- Game Creation ---

# PUBLIC_INTERFACE
@app.post("/games/", response_model=GameRead, summary="Create new game", tags=["Game"])
def create_game(game_in: GameCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Create a new game, optionally vs a specific opponent.
    If opponent is not given, game is created with user2 as NULL ("waiting" status).
    """
    opponent = None
    if game_in.opponent_username:
        opponent = db.query(User).filter(User.username == game_in.opponent_username).first()
        if not opponent:
            raise HTTPException(status_code=404, detail="Opponent not found.")
        if opponent.id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot play a game against yourself.")
        game = Game(user1_id=current_user.id, user2_id=opponent.id, status=GameStatus.in_progress)
    else:
        game = Game(user1_id=current_user.id, user2_id=None, status=GameStatus.waiting)
    db.add(game)
    db.commit()
    db.refresh(game)
    return game

# --- Join Waiting Game ---

@app.post("/games/join", response_model=GameRead, summary="Join a waiting game as opponent", tags=["Game"])
def join_waiting_game(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Join an open waiting game if available (not already in a game).
    """
    waiting_game = db.query(Game).filter(Game.status == GameStatus.waiting, Game.user1_id != current_user.id).first()
    if not waiting_game:
        raise HTTPException(status_code=404, detail="No available games to join.")
    waiting_game.user2_id = current_user.id
    waiting_game.status = GameStatus.in_progress
    db.commit()
    db.refresh(waiting_game)
    return waiting_game

# --- List User's Games ---

# PUBLIC_INTERFACE
@app.get("/games/", response_model=List[GameRead], summary="List all games of current user", tags=["Game"])
def list_my_games(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    List all games for which the current user is a player.
    """
    games = db.query(Game).filter((Game.user1_id == current_user.id) | (Game.user2_id == current_user.id)).order_by(Game.created_at.desc()).all()
    return games

# --- Get Game Details (w/ Moves) ---

# PUBLIC_INTERFACE
@app.get("/games/{game_id}", response_model=GameDetail, summary="Get details of a game including moves", tags=["Game"])
def get_game_detail(game_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Get a game and its move list. Only allowed if you're a player in this game.
    """
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game or (game.user1_id != current_user.id and game.user2_id != current_user.id):
        raise HTTPException(status_code=404, detail="Game not found or not permitted.")
    moves = db.query(Move).filter(Move.game_id == game.id).order_by(Move.move_number).all()
    return GameDetail(
        id=game.id,
        user1_id=game.user1_id,
        user2_id=game.user2_id,
        status=game.status,
        created_at=game.created_at,
        winner_id=game.winner_id,
        moves=moves,
    )

# --- Make Move ---

# PUBLIC_INTERFACE
@app.post("/moves/", response_model=MoveRead, summary="Make a move in a game", tags=["Move"])
def make_move(move_in: MoveCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Submit a move. Validates it's user's turn, cell is empty, and applies game rules:
    - Validates player turn
    - Checks cell not taken
    - Records the move
    - Updates game status (win/draw/continue)
    Persists all changes in the DB.
    """
    # 1. Fetch game and ensure user permission/participation
    game = db.query(Game).filter(Game.id == move_in.game_id).first()
    if not game or (current_user.id not in [game.user1_id, game.user2_id]):
        raise HTTPException(status_code=404, detail="Game not found/permission denied.")
    # 2. Ensure game is in progress and opponent joined
    if game.status != GameStatus.in_progress:
        raise HTTPException(status_code=400, detail="Game is not in progress.")
    if game.user2_id is None:
        raise HTTPException(status_code=403, detail="Second player hasn't joined this game yet.")
    # 3. Fetch moves, construct logic board, enforce turn order and cell occupancy
    moves = db.query(Move).filter(Move.game_id == game.id).order_by(Move.move_number).all()
    # Use new logic:
    try:
        validate_and_get_next_player(moves, game.user1_id, game.user2_id, current_user.id)
        board = create_board_from_moves(moves, game.user1_id, game.user2_id)
        is_cell_empty(board, move_in.row, move_in.col)
    except NotPlayersTurn:
        raise HTTPException(status_code=400, detail="Not your turn.")
    except CellOccupied:
        raise HTTPException(status_code=400, detail="Cell already taken.")
    except InvalidMove as e:
        raise HTTPException(status_code=400, detail=str(e))
    # 4. Apply and persist move
    move = Move(
        game_id=game.id,
        user_id=current_user.id,
        row=move_in.row,
        col=move_in.col,
        move_number=len(moves) + 1,
    )
    db.add(move)
    db.commit()
    db.refresh(move)
    # 5. Recreate board including the new move and check for win/draw
    moves_post = moves + [move]
    board_post = create_board_from_moves(moves_post, game.user1_id, game.user2_id)
    winner_id = check_winner(board_post, game.user1_id, game.user2_id)
    game_ended = False
    if winner_id:
        game.status = GameStatus.finished
        game.winner_id = winner_id
        game_ended = True
    elif is_board_full(moves_post):
        game.status = GameStatus.finished
        game_ended = True
    if game_ended:
        db.commit()
    return move


# --- Get User Game History ---

# PUBLIC_INTERFACE
@app.get("/history/", response_model=UserHistory, summary="Get user's game history", tags=["User"])
def get_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Returns a summary of the user's games for history display.
    """
    games = db.query(Game).filter((Game.user1_id == current_user.id) | (Game.user2_id == current_user.id)).order_by(Game.created_at.desc()).all()
    summaries = []
    for g in games:
        opponent_id = g.user2_id if g.user1_id == current_user.id else g.user1_id
        opponent = db.query(User).filter(User.id == opponent_id).first() if opponent_id else None
        winner = db.query(User).filter(User.id == g.winner_id).first() if g.winner_id else None
        summaries.append(GameSummary(
            id=g.id,
            opponent=opponent.username if opponent else "(waiting)",
            status=g.status,
            created_at=g.created_at,
            winner=winner.username if winner else None,
        ))
    return UserHistory(games=summaries)

"""
Database configuration:
-----------------------
- By default, uses SQLite (file: tic_tac_toe.db in backend root).
- For production, set environment variables:
    POSTGRES_USER
    POSTGRES_PASSWORD
    POSTGRES_DB
    POSTGRES_HOST
    POSTGRES_PORT (default 5432)
- The backend will auto-connect to PostgreSQL if all these are set, else falls back to SQLite.

Example for .env (if using a tool like python-dotenv or docker-compose):
POSTGRES_USER=myuser
POSTGRES_PASSWORD=mypass
POSTGRES_DB=tictactoe
POSTGRES_HOST=postgres-db
POSTGRES_PORT=5432

Database schema overview:
------------------------
- Users: user registration, login, identity
- Games: tracks tic tac toe matches, users, status, winner
- Moves: stores every move, sequence, position, who moved

Table creation is automatic; no manual intervention required on startup.
"""
