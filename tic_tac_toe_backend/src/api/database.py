import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Environment variable selection, falls back to SQLite for local dev/testing
POSTGRES_USER = os.getenv("POSTGRES_USER", "")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
POSTGRES_DB = os.getenv("POSTGRES_DB", "")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

if POSTGRES_USER and POSTGRES_PASSWORD and POSTGRES_DB and POSTGRES_HOST:
    SQLALCHEMY_DATABASE_URL = (
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
else:
    SQLALCHEMY_DATABASE_URL = "sqlite:///./tic_tac_toe.db"

# For SQLite: set "check_same_thread=False"
extra_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    extra_args = {"connect_args": {"check_same_thread": False}}

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True, **extra_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# PUBLIC_INTERFACE
def get_db():
    """
    Dependency-injected database session generator for FastAPI routes.
    Yields an open SQLAlchemy session which is closed when done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
