# Task API — Docker + PostgreSQL

The Task API runs together with PostgreSQL via Docker Compose. Task data is stored in PostgreSQL's named `postgres_data` volume, so it remains available after restarting the app or database container.

## Start everything

1. Copy `.env.example` to `.env` and set a non-default local password if desired.
2. From this directory, run:

   ```bash
   docker compose up --build
   ```

3. Open the API at <http://localhost:8000> or the interactive API docs at <http://localhost:8000/docs>.

The app container logs `Uvicorn running on http://0.0.0.0:8000`. `0.0.0.0` means the server is listening on every network interface **inside the container**; use `localhost:8000` from your browser on the host computer.

To stop the stack without removing persisted data, use `docker compose down`. Do **not** use `docker compose down -v` unless you deliberately want to delete the database volume.

## Configuration and schema

`DATABASE_URL` comes from `.env`; the file is gitignored. `.env.example` is committed as the safe template. The database container also receives `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` from that file.

The table schema is in [init.sql](init.sql). PostgreSQL runs it when its named volume is first created. The API also uses `CREATE TABLE IF NOT EXISTS` at startup so the service can safely initialize an existing empty database.

## Repository layering

`TaskService` depends only on the `TaskRepository` contract in [repository.py](repository.py). Both [in_memory_repository.py](in_memory_repository.py) and [postgres_repository.py](postgres_repository.py) implement that contract. The composition line in `main.py` selects `PostgresTaskRepository`.

The service logic and HTTP routes do not contain PostgreSQL queries and do not change when storage is swapped: selecting `InMemoryTaskRepository()` instead is the only application wiring change needed for an ephemeral test store. The public routes, request bodies, response models, validation, and status codes are unchanged.

## Persistence check

Use these commands after `docker compose up --build`:

```bash
curl -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d '{"title":"survives restart"}'
curl http://localhost:8000/tasks
docker compose restart db app
curl http://localhost:8000/tasks
```

The task titled `survives restart` should appear in both list responses. This restarts the application and PostgreSQL containers while retaining `postgres_data`; only `docker compose down -v` removes it.

## Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/` | API information |
| GET | `/health` | Health check |
| GET | `/tasks` | List tasks; supports `done`, `search`, `sort`, `limit`, and `offset` |
| GET | `/stats` | Total, completed, and open task counts |
| POST | `/reset` | Restore the original sample tasks |
| GET | `/tasks/{id}` | Get a task |
| POST | `/tasks` | Create a task |
| PUT | `/tasks/{id}` | Update a task |
| DELETE | `/tasks/{id}` | Delete a task |
