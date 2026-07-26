"""Pydantic models for the task API."""

from typing import Optional

from pydantic import BaseModel


class Task(BaseModel):
    """Response model for a task."""

    id: int
    title: str
    done: bool


class TaskCreate(BaseModel):
    """Request model for creating a task."""

    title: Optional[str] = None


class TaskUpdate(BaseModel):
    """Request model for updating a task."""

    title: Optional[str] = None
    done: Optional[bool] = None
