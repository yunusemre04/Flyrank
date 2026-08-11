"""Repository contract shared by alternate task storage implementations."""

from typing import Optional, Protocol

from models import Task


class TaskRepository(Protocol):
    """Storage operations required by the task service."""

    def initialize(self) -> None: ...

    def list_tasks(
        self,
        done: Optional[bool] = None,
        search: Optional[str] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[Task]: ...

    def get_by_id(self, task_id: int) -> Optional[Task]: ...

    def create(self, title: str) -> Task: ...

    def update(self, task: Task) -> Task: ...

    def delete(self, task_id: int) -> None: ...

    def statistics(self) -> tuple[int, int, int]: ...

    def reset(self) -> list[Task]: ...
