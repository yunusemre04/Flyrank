"""HTTP routes for the PostgreSQL-backed task API."""

from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, status

from models import ResetResponse, Task, TaskCreate, TaskStats, TaskUpdate
from postgres_repository import PostgresTaskRepository
from task_service import TaskService

app = FastAPI(
    title="Task API",
    version="1.0",
    description="A beginner-friendly FastAPI project backed by PostgreSQL.",
)
service = TaskService(PostgresTaskRepository())


@app.on_event("startup")
def startup_event() -> None:
    service.initialize()


@app.get("/", summary="API information", description="Return API metadata.")
def root() -> dict:
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Health check", description="Check whether the API is running.")
def health_check() -> dict:
    return {"status": "ok"}


@app.get("/tasks", response_model=List[Task], summary="List tasks")
def list_tasks(
    done: Optional[bool] = Query(default=None, description="Filter by completion status."),
    search: Optional[str] = Query(default=None, description="Case-insensitive search term."),
    sort: Optional[str] = Query(default=None, description="title or -title."),
    limit: Optional[int] = Query(default=None, description="Maximum tasks to return."),
    offset: int = Query(default=0, description="Number of tasks to skip."),
) -> List[Task]:
    return service.list_tasks(done, search, sort, limit, offset)


@app.get("/stats", response_model=TaskStats, summary="Task statistics")
def task_stats() -> TaskStats:
    return service.statistics()


@app.post("/reset", response_model=ResetResponse, summary="Reset tasks")
def reset_tasks() -> ResetResponse:
    return ResetResponse(message="Tasks reset successfully", tasks=service.reset())


@app.get("/tasks/{task_id}", response_model=Task, summary="Get task by id")
def get_task(task_id: int) -> Task:
    return service.get(task_id)


@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED, summary="Create task")
def create_task(payload: TaskCreate) -> Task:
    return service.create(payload.title)


@app.put("/tasks/{task_id}", response_model=Task, summary="Update task")
def update_task(task_id: int, payload: TaskUpdate) -> Task:
    return service.update(task_id, payload)


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete task")
def delete_task(task_id: int) -> None:
    service.delete(task_id)
