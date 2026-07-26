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
| GET | /tasks/{id} | Get one task |
| POST | /tasks | Create a task |
| PUT | /tasks/{id} | Update a task |
| DELETE | /tasks/{id} | Delete a task |

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
