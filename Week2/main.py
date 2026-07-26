"""FastAPI application for a SQLite-backed task API."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator, List, Optional

from fastapi import FastAPI, HTTPException, Query, status

from models import ResetResponse, Task, TaskCreate, TaskStats, TaskUpdate


app = FastAPI(
    title="Task API",
    version="1.0",
    description="A beginner-friendly FastAPI project that stores tasks only in memory.",
)


# SQLite database stored alongside this file.
DATABASE_PATH = Path(__file__).with_name("tasks.db")

# Original example tasks used for seeding and reset.
ORIGINAL_TASKS: List[Task] = [
    Task(id=1, title="Learn FastAPI", done=False),
    Task(id=2, title="Build a simple API", done=False),
    Task(id=3, title="Test the endpoints", done=True),
]


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Yield a SQLite connection and close it after use."""

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def row_to_task(row: sqlite3.Row) -> Task:
    """Convert a SQLite row into the task response model."""

    return Task(id=row["id"], title=row["title"], done=bool(row["done"]))


def seed_database(connection: sqlite3.Connection) -> None:
    """Insert the three original example tasks into the database."""

    connection.execute("DELETE FROM sqlite_sequence WHERE name = ?", ("tasks",))
    connection.executemany(
        "INSERT INTO tasks(title, done) VALUES (?, ?)",
        [(task.title, int(task.done)) for task in ORIGINAL_TASKS],
    )


def initialize_database() -> None:
    """Create the database table and seed it when empty."""

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done BOOLEAN NOT NULL
            )
            """
        )
        row = connection.execute("SELECT COUNT(*) FROM tasks").fetchone()
        if row is not None and row[0] == 0:
            seed_database(connection)


@app.on_event("startup")
def startup_event() -> None:
    """Initialize the database when the application starts."""

    initialize_database()


def get_task_by_id(task_id: int) -> Optional[Task]:
    """Return a task by id or None if it does not exist."""

    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

    if row is None:
        return None
    return row_to_task(row)


def get_task_statistics() -> TaskStats:
    """Return aggregate information about the current task table."""

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS total,
                COUNT(CASE WHEN done = 1 THEN 1 END) AS done,
                COUNT(CASE WHEN done = 0 THEN 1 END) AS open
            FROM tasks
            """
        ).fetchone()

    return TaskStats(total=row["total"], done=row["done"], open=row["open"])


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


def get_tasks_from_database(
    done: Optional[bool] = None,
    search: Optional[str] = None,
    sort: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[Task]:
    """Return tasks after applying filter, search, sort, and pagination."""

    query = "SELECT * FROM tasks"
    where_clauses: List[str] = []
    parameters: List[object] = []

    if done is not None:
        where_clauses.append("done = ?")
        parameters.append(int(done))

    if search is not None:
        where_clauses.append("title LIKE ? COLLATE NOCASE")
        parameters.append(f"%{search.strip()}%")

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    if sort == "title":
        query += " ORDER BY title ASC"
    elif sort == "-title":
        query += " ORDER BY title DESC"
    else:
        query += " ORDER BY id ASC"

    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        parameters.extend([limit, offset])
    elif offset:
        query += " LIMIT -1 OFFSET ?"
        parameters.append(offset)

    with get_connection() as connection:
        rows = connection.execute(query, parameters).fetchall()

    return [row_to_task(row) for row in rows]


def reset_database() -> List[Task]:
    """Restore the database to the original three example tasks."""

    with get_connection() as connection:
        connection.execute("DELETE FROM tasks")
        seed_database(connection)

    return get_tasks_from_database()


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
    sort: Optional[str] = Query(
        default=None,
        description="Sort by title or use -title for descending order.",
    ),
    limit: Optional[int] = Query(default=None, description="Maximum tasks to return"),
    offset: int = Query(default=0, description="Number of tasks to skip"),
) -> List[Task]:
    """Return the full list of tasks."""

    validate_pagination(limit=limit, offset=offset)
    return get_tasks_from_database(
        done=done,
        search=search,
        sort=sort,
        limit=limit,
        offset=offset,
    )


@app.get(
    "/stats",
    response_model=TaskStats,
    summary="Task statistics",
    description="Return total, completed, and open task counts.",
)
def task_stats() -> TaskStats:
    """Return statistics for the current database rows."""

    return get_task_statistics()


@app.post(
    "/reset",
    response_model=ResetResponse,
    summary="Reset tasks",
    description="Restore the original example tasks and remove all changes.",
)
def reset_tasks() -> ResetResponse:
    """Reset the task list back to the original three example tasks."""

    restored_tasks = reset_database()
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
    """Create and store a new task in the database."""

    cleaned_title = validate_title(payload.title)
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO tasks(title, done) VALUES (?, ?)",
            (cleaned_title, 0),
        )

    return Task(id=cursor.lastrowid, title=cleaned_title, done=False)


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

    updated_title = task.title
    updated_done = task.done

    if payload.title is not None:
        updated_title = validate_title(payload.title)
    if payload.done is not None:
        updated_done = payload.done

    with get_connection() as connection:
        connection.execute(
            "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
            (updated_title, int(updated_done), task_id),
        )

    return Task(id=task_id, title=updated_title, done=updated_done)


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

    with get_connection() as connection:
        connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
