from datetime import datetime

from pydantic import BaseModel

STATUSES = {"backlog", "todo", "in_progress", "review", "blocked", "done", "canceled"}
PRIORITIES = {"low", "medium", "high", "urgent"}


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    priority: str = "medium"
    due_date: datetime | None = None
    assignee_kind: str | None = None  # user|agent
    assignee_id: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    due_date: datetime | None = None


class StatusChange(BaseModel):
    status: str


class AssignIn(BaseModel):
    assignee_kind: str  # user|agent
    assignee_id: str


class CommentIn(BaseModel):
    body: str


class TaskOut(BaseModel):
    id: str
    project_id: str
    title: str
    description: str | None
    status: str
    priority: str
    due_date: datetime | None
    assignee_kind: str | None
    assignee_id: str | None
