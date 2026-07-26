# Task API

Task API is a beginner-friendly FastAPI project backed by SQLite. The API keeps the same routes and request/response models, but task data is now stored in `tasks.db` instead of an in-memory list.

## Why SQLite

SQLite is a good fit for this assignment because it is built into Python, requires no extra server, and keeps the code simple while still supporting persistent storage.

## Database location

The database file is created automatically next to the application file:

`Week2/tasks.db`

## Automatic setup

When the app starts, it automatically:

1. Creates `tasks.db` if it does not exist.
2. Creates the `tasks` table if it does not exist.
3. Seeds the database with the original three example tasks only when the table is empty.

If you delete `tasks.db`, the next server start recreates it and seeds the example data again.

## Installation

Install the dependencies with:

```bash
pip install -r requirements.txt
```

## Run the server

Start the API with:

```bash
uvicorn main:app --reload
```

## DB Browser screenshot placeholder

Open `tasks.db` in DB Browser for SQLite and add a screenshot here after verifying the seeded rows.

## Example SQL query

```sql
SELECT * FROM tasks;
```

## Swagger UI

Open the interactive API documentation at:

http://localhost:8000/docs

## Endpoint table

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | / | API information |
| GET | /health | Health check |
| GET | /tasks | List all tasks |
| GET | /stats | Task statistics |
| POST | /reset | Reset tasks to the original examples |
| GET | /tasks/{id} | Get one task |
| POST | /tasks | Create a task |
| PUT | /tasks/{id} | Update a task |
| DELETE | /tasks/{id} | Delete a task |

## Filtering

Use `done=true` or `done=false` to filter tasks by completion status.

```bash
curl "http://localhost:8000/tasks?done=true"
```

## Search

Search task titles with the `search` query parameter.

```bash
curl "http://localhost:8000/tasks?search=milk"
```

## Sorting

Sort tasks by title with `sort=title` or reverse the order with `sort=-title`.

```bash
curl "http://localhost:8000/tasks?sort=title"
curl "http://localhost:8000/tasks?sort=-title"
```

## Statistics

Get the current task totals with `/stats`.

```bash
curl http://localhost:8000/stats
```

## Reset

Restore the original three example tasks with `/reset`.

```bash
curl -X POST http://localhost:8000/reset
```

## Pagination

Use `limit` and `offset` together with filtering and search.

```bash
curl "http://localhost:8000/tasks?limit=2&offset=0"
```

## Example curl commands

### GET /

```bash
curl http://localhost:8000/
```

### GET /health

```bash
curl http://localhost:8000/health
```

### GET /tasks

```bash
curl http://localhost:8000/tasks
```

### GET /tasks?done=true

```bash
curl "http://localhost:8000/tasks?done=true"
```

### GET /tasks?done=false

```bash
curl "http://localhost:8000/tasks?done=false"
```

### GET /tasks?search=milk

```bash
curl "http://localhost:8000/tasks?search=milk"
```

### GET /tasks?done=true&search=project

```bash
curl "http://localhost:8000/tasks?done=true&search=project"
```

### GET /tasks?sort=title

```bash
curl "http://localhost:8000/tasks?sort=title"
```

### GET /tasks?sort=-title

```bash
curl "http://localhost:8000/tasks?sort=-title"
```

### GET /tasks?limit=2

```bash
curl "http://localhost:8000/tasks?limit=2"
```

### GET /tasks?offset=2

```bash
curl "http://localhost:8000/tasks?offset=2"
```

### GET /tasks?limit=2&offset=2

```bash
curl "http://localhost:8000/tasks?limit=2&offset=2"
```

### GET /tasks/{id}

```bash
curl http://localhost:8000/tasks/1
```

### POST /tasks

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Buy milk"}'
```

### PUT /tasks/{id}

```bash
curl -X PUT http://localhost:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"done":true}'
```

### DELETE /tasks/{id}

```bash
curl -X DELETE http://localhost:8000/tasks/1
```

### GET /stats

```bash
curl http://localhost:8000/stats
```

### POST /reset

```bash
curl -X POST http://localhost:8000/reset
```
