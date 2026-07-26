# Task API

Task API is a beginner-friendly FastAPI project that stores all data in an in-memory Python list. No database, ORM, or file storage is used, so every restart clears the data.

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
