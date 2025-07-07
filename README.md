# tictacconnect-36024-a6347dcf

## Database Integration

This backend supports both PostgreSQL (recommended for production) and SQLite (fallback for development/local/test).

### Tables

- **users**: (id, username, email, hashed_password)
- **games**: (id, user1_id, user2_id, status, created_at, winner_id)
- **moves**: (id, game_id, user_id, row, col, move_number, created_at)

### Switching databases

- **PostgreSQL**: Set all these environment variables before starting the backend:
  - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, 

     Optional: `POSTGRES_PORT` (default: 5432)
- **SQLite fallback**: If any PG variable is missing, will use `tic_tac_toe.db` file in backend root

### Alembic Migrations

- Alembic is included for future production migrations. Initialize with:
  ```
  alembic init alembic
  ```
  (see Alembic docs for usage).

### Table Initialization

- All tables auto-create on startup (see `main.py` for the startup event).
- No manual SQL is necessary.
- To reset DB in dev, simply delete `tic_tac_toe.db` file when using SQLite.

### Further Configuration

For custom production setup, mount your own PostgreSQL and pass variables (Docker, cloud, or env file).
