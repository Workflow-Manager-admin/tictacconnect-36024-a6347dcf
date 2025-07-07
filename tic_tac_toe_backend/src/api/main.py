from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import models
from .database import engine

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    # Creates tables if they don't exist already (safe for dev/demo)
    models.Base.metadata.create_all(bind=engine)

@app.get("/")
def health_check():
    return {"message": "Healthy"}

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
