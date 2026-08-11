"""Reference in-memory repository; useful for isolated service tests."""

from typing import Optional

from models import Task
from seed_data import ORIGINAL_TASKS


class InMemoryTaskRepository:
    """Implements TaskRepository without durable storage."""

    def __init__(self) -> None:
        self.tasks: list[Task] = []
        self.next_id = 1

    def initialize(self) -> None:
        if not self.tasks:
            self.reset()

    def list_tasks(self, done=None, search=None, sort=None, limit=None, offset=0) -> list[Task]:
        tasks = self.tasks
        if done is not None:
            tasks = [task for task in tasks if task.done == done]
        if search is not None:
            tasks = [task for task in tasks if search.strip().lower() in task.title.lower()]
        tasks = sorted(tasks, key=lambda task: task.title if sort in ("title", "-title") else task.id, reverse=sort == "-title")
        return tasks[offset:] if limit is None else tasks[offset : offset + limit]

    def get_by_id(self, task_id: int) -> Optional[Task]:
        return next((task for task in self.tasks if task.id == task_id), None)

    def create(self, title: str) -> Task:
        task = Task(id=self.next_id, title=title, done=False)
        self.tasks.append(task)
        self.next_id += 1
        return task

    def update(self, task: Task) -> Task:
        return task

    def delete(self, task_id: int) -> None:
        self.tasks = [task for task in self.tasks if task.id != task_id]

    def statistics(self) -> tuple[int, int, int]:
        done = sum(task.done for task in self.tasks)
        return len(self.tasks), done, len(self.tasks) - done

    def reset(self) -> list[Task]:
        self.tasks = [Task(id=index, title=title, done=done) for index, (title, done) in enumerate(ORIGINAL_TASKS, 1)]
        self.next_id = len(self.tasks) + 1
        return self.tasks
