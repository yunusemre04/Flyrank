"""Application rules; this layer does not know which database is in use."""

from typing import Optional

from fastapi import HTTPException, status

from models import Task, TaskStats, TaskUpdate
from repository import TaskRepository


class TaskService:
    """Task use-cases shared by all repository implementations."""

    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    def initialize(self) -> None:
        self.repository.initialize()

    @staticmethod
    def _title(title: Optional[str]) -> str:
        if title is None or not title.strip():
            raise HTTPException(status_code=400, detail={"error": "Title is required"})
        return title.strip()

    @staticmethod
    def _not_found(task_id: int) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": f"Task {task_id} not found"},
        )

    def list_tasks(self, done, search, sort, limit, offset) -> list[Task]:
        if limit is not None and limit <= 0:
            raise HTTPException(status_code=400, detail={"error": "Limit must be positive"})
        if offset < 0:
            raise HTTPException(status_code=400, detail={"error": "Offset must be greater than or equal to 0"})
        return self.repository.list_tasks(done, search, sort, limit, offset)

    def get(self, task_id: int) -> Task:
        task = self.repository.get_by_id(task_id)
        if task is None:
            raise self._not_found(task_id)
        return task

    def create(self, title: Optional[str]) -> Task:
        return self.repository.create(self._title(title))

    def update(self, task_id: int, payload: TaskUpdate) -> Task:
        task = self.get(task_id)
        if payload.title is None and payload.done is None:
            raise HTTPException(status_code=400, detail={"error": "At least one field must be provided"})
        if payload.title is not None:
            task.title = self._title(payload.title)
        if payload.done is not None:
            task.done = payload.done
        return self.repository.update(task)

    def delete(self, task_id: int) -> None:
        self.get(task_id)
        self.repository.delete(task_id)

    def statistics(self) -> TaskStats:
        total, done, open_tasks = self.repository.statistics()
        return TaskStats(total=total, done=done, open=open_tasks)

    def reset(self) -> list[Task]:
        return self.repository.reset()
