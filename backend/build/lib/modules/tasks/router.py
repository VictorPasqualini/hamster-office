from fastapi import APIRouter, Depends
from sqlalchemy import select

from ...core.deps import TenantCtx, tenant_ctx
from ...core.events import record_audit
from ...core.exceptions import AppError, NotFound
from ...db.models import Task, TaskComment
from .schemas import (
    PRIORITIES,
    STATUSES,
    AssignIn,
    CommentIn,
    StatusChange,
    TaskCreate,
    TaskOut,
    TaskUpdate,
)

router = APIRouter(tags=["tasks"])


def _out(t: Task) -> TaskOut:
    return TaskOut(
        id=str(t.id),
        project_id=str(t.project_id),
        title=t.title,
        description=t.description,
        status=t.status,
        priority=t.priority,
        due_date=t.due_date,
        assignee_kind=t.assignee_kind,
        assignee_id=str(t.assignee_id) if t.assignee_id else None,
    )


@router.post("/projects/{project_id}/tasks", response_model=TaskOut, status_code=201)
async def create_task(project_id: str, body: TaskCreate, ctx: TenantCtx = Depends(tenant_ctx)):
    ctx.require("collaborator")
    if body.priority not in PRIORITIES:
        raise AppError("Prioridade inválida")
    t = Task(
        workspace_id=ctx.workspace_id,
        project_id=project_id,
        title=body.title,
        description=body.description,
        priority=body.priority,
        due_date=body.due_date,
        assignee_kind=body.assignee_kind,
        assignee_id=body.assignee_id,
        created_by_kind="user",
        created_by_id=ctx.membership_id,
    )
    ctx.db.add(t)
    await ctx.db.flush()
    await record_audit(
        ctx.db,
        workspace_id=ctx.workspace_id,
        type_="task.created",
        actor_kind="user",
        actor_id=ctx.membership_id,
        target_kind="task",
        target_id=t.id,
        payload={"title": t.title},
    )
    return _out(t)


@router.get("/projects/{project_id}/tasks", response_model=list[TaskOut])
async def list_tasks(
    project_id: str, status: str | None = None, ctx: TenantCtx = Depends(tenant_ctx)
):
    q = select(Task).where(Task.project_id == project_id)
    if status:
        q = q.where(Task.status == status)
    rows = await ctx.db.scalars(q.order_by(Task.board_order, Task.created_at))
    return [_out(t) for t in rows]


async def _get(ctx: TenantCtx, task_id: str) -> Task:
    t = await ctx.db.scalar(select(Task).where(Task.id == task_id))
    if not t:
        raise NotFound("Tarefa não encontrada")
    return t


@router.get("/tasks/{task_id}", response_model=TaskOut)
async def get_task(task_id: str, ctx: TenantCtx = Depends(tenant_ctx)):
    return _out(await _get(ctx, task_id))


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def update_task(task_id: str, body: TaskUpdate, ctx: TenantCtx = Depends(tenant_ctx)):
    ctx.require("collaborator")
    t = await _get(ctx, task_id)
    data = body.model_dump(exclude_unset=True)
    if "priority" in data and data["priority"] not in PRIORITIES:
        raise AppError("Prioridade inválida")
    for field, value in data.items():
        setattr(t, field, value)
    return _out(t)


@router.post("/tasks/{task_id}/status", response_model=TaskOut)
async def change_status(task_id: str, body: StatusChange, ctx: TenantCtx = Depends(tenant_ctx)):
    ctx.require("collaborator")
    if body.status not in STATUSES:
        raise AppError("Status inválido")
    t = await _get(ctx, task_id)
    old = t.status
    t.status = body.status
    await record_audit(
        ctx.db,
        workspace_id=ctx.workspace_id,
        type_="task.status_changed",
        actor_kind="user",
        actor_id=ctx.membership_id,
        target_kind="task",
        target_id=t.id,
        payload={"from": old, "to": body.status},
    )
    return _out(t)


@router.post("/tasks/{task_id}/assign", response_model=TaskOut)
async def assign_task(task_id: str, body: AssignIn, ctx: TenantCtx = Depends(tenant_ctx)):
    ctx.require("collaborator")
    if body.assignee_kind not in {"user", "agent"}:
        raise AppError("assignee_kind inválido")
    t = await _get(ctx, task_id)
    t.assignee_kind = body.assignee_kind
    t.assignee_id = body.assignee_id
    return _out(t)


@router.post("/tasks/{task_id}/comments", status_code=201)
async def comment(task_id: str, body: CommentIn, ctx: TenantCtx = Depends(tenant_ctx)):
    await _get(ctx, task_id)
    c = TaskComment(
        workspace_id=ctx.workspace_id,
        task_id=task_id,
        author_kind="user",
        author_id=ctx.membership_id,
        body=body.body,
    )
    ctx.db.add(c)
    await ctx.db.flush()
    return {"id": str(c.id)}
