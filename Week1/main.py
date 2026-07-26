"""FastAPI application for an in-memory task API."""

from copy import deepcopy
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, status

from models import ResetResponse, Task, TaskCreate, TaskStats, TaskUpdate


app = FastAPI(
    title="Task API",
    version="1.0",
    description="A beginner-friendly FastAPI project that stores tasks only in memory.",
)


# In-memory storage only. Data is lost whenever the server restarts.
ORIGINAL_TASKS: List[Task] = [
    Task(id=1, title="Learn FastAPI", done=False),
    Task(id=2, title="Build a simple API", done=False),
    Task(id=3, title="Test the endpoints", done=True),
]

tasks: List[Task] = deepcopy(ORIGINAL_TASKS)


def get_task_by_id(task_id: int) -> Optional[Task]:
    """Return a task from the in-memory list or None if it does not exist."""

    for task in tasks:
        if task.id == task_id:
            return task
    return None


def get_next_task_id() -> int:
    """Return the next available task id."""

    if not tasks:
        return 1
    return max(task.id for task in tasks) + 1


def get_filtered_tasks(
    done: Optional[bool] = None,
    search: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[Task]:
    """Return tasks after applying filter, search, and pagination rules."""

    filtered_tasks = tasks

    if done is not None:
        filtered_tasks = [task for task in filtered_tasks if task.done == done]

    if search is not None:
        search_term = search.strip().lower()
        filtered_tasks = [
            task for task in filtered_tasks if search_term in task.title.lower()
        ]

    if offset:
        filtered_tasks = filtered_tasks[offset:]

    if limit is not None:
        filtered_tasks = filtered_tasks[:limit]

    return filtered_tasks


def validate_pagination(limit: Optional[int], offset: int) -> None:
    """Validate pagination query parameters."""

    if limit is not None and limit <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Limit must be positive"},
        )

    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Offset must be greater than or equal to 0"},
        )


def reset_task_list() -> List[Task]:
    """Restore the in-memory task list to the original example tasks."""

    global tasks
    tasks = deepcopy(ORIGINAL_TASKS)
    return tasks


def get_task_statistics() -> TaskStats:
    """Return aggregate information about the current task list."""

    completed_tasks = sum(1 for task in tasks if task.done)
    return TaskStats(
        total=len(tasks),
        done=completed_tasks,
        open=len(tasks) - completed_tasks,
    )


def validate_title(title: Optional[str]) -> str:
    """Validate a task title and return the cleaned value."""

    if title is None or title.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Title is required"},
        )
    return title.strip()


def validate_update_payload(payload: TaskUpdate) -> None:
    """Ensure the update request contains at least one valid field."""

    if payload.title is None and payload.done is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "At least one field must be provided"},
        )


@app.get(
    "/",
    summary="API information",
    description="Return the name, version, and main endpoint for the API.",
)
def root() -> dict:
    """Return basic metadata about the API."""

    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get(
    "/health",
    summary="Health check",
    description="Check whether the API is running.",
)
def health_check() -> dict:
    """Return a simple health status."""

    return {"status": "ok"}


@app.get(
    "/tasks",
    response_model=List[Task],
    summary="List tasks",
    description=(
        "Return tasks from memory with optional filtering, search, and "
        "pagination."
    ),
)
def list_tasks(
    done: Optional[bool] = Query(
        default=None,
        description="Filter tasks by completion status.",
    ),
    search: Optional[str] = Query(
        default=None,
        description="Case-insensitive search term for task titles.",
    ),
    limit: Optional[int] = Query(default=None, description="Maximum tasks to return"),
    offset: int = Query(default=0, description="Number of tasks to skip"),
) -> List[Task]:
    """Return the full list of tasks."""

    validate_pagination(limit=limit, offset=offset)
    return get_filtered_tasks(done=done, search=search, limit=limit, offset=offset)


@app.get(
    "/stats",
    response_model=TaskStats,
    summary="Task statistics",
    description="Return total, completed, and open task counts.",
)
def task_stats() -> TaskStats:
    """Return statistics for the current in-memory tasks."""

    return get_task_statistics()


@app.post(
    "/reset",
    response_model=ResetResponse,
    summary="Reset tasks",
    description="Restore the original example tasks and remove all changes.",
)
def reset_tasks() -> ResetResponse:
    """Reset the task list back to the original three example tasks."""

    restored_tasks = reset_task_list()
    return ResetResponse(
        message="Tasks reset successfully",
        tasks=restored_tasks,
    )


@app.get(
    "/tasks/{task_id}",
    response_model=Task,
    summary="Get task by id",
    description="Return a single task by its id.",
)
def get_task(task_id: int) -> Task:
    """Return one task or raise a 404 error if it does not exist."""

    task = get_task_by_id(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": f"Task {task_id} not found"},
        )
    return task


@app.post(
    "/tasks",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
    summary="Create task",
    description="Create a new task with a title and an automatic id.",
)
def create_task(payload: TaskCreate) -> Task:
    """Create and store a new task in memory."""

    cleaned_title = validate_title(payload.title)
    new_task = Task(id=get_next_task_id(), title=cleaned_title, done=False)
    tasks.append(new_task)
    return new_task


@app.put(
    "/tasks/{task_id}",
    response_model=Task,
    summary="Update task",
    description="Update the title and/or done status of an existing task.",
)
def update_task(task_id: int, payload: TaskUpdate) -> Task:
    """Update an existing task and return the updated record."""

    task = get_task_by_id(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": f"Task {task_id} not found"},
        )

    validate_update_payload(payload)

    if payload.title is not None:
        task.title = validate_title(payload.title)
    if payload.done is not None:
        task.done = payload.done

    return task


@app.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task",
    description="Delete a task from the in-memory list.",
)
def delete_task(task_id: int) -> None:
    """Delete a task or raise a 404 error if it does not exist."""

    task = get_task_by_id(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": f"Task {task_id} not found"},
        )

    tasks.remove(task)
