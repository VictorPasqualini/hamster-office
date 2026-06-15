"""Modelos SQLAlchemy do MVP (fonte única do schema, criado pelo bootstrap).

Organizado por bounded context / schema. Tabelas de negócio carregam `workspace_id`
para o isolamento multi-tenant (RLS aplicada no bootstrap).
"""

import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..core.config import settings
from .base import Base, TimestampMixin

UUIDpk = UUID(as_uuid=True)


# ----------------------------------------------------------------------------- auth
class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = {"schema": "auth"}
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ------------------------------------------------------------------------ workspace
class Workspace(Base, TimestampMixin):
    __tablename__ = "workspaces"
    __table_args__ = {"schema": "workspace"}
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    plan: Mapped[str] = mapped_column(String(20), default="free")
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth.users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="active")


class WorkspaceSettings(Base):
    __tablename__ = "settings"
    __table_args__ = {"schema": "workspace"}
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspace.workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    default_model: Mapped[str] = mapped_column(String(80), default="qwen3:8b")
    monthly_token_budget: Mapped[int | None] = mapped_column(Integer)
    office_theme: Mapped[str] = mapped_column(String(40), default="classic")


class Membership(Base, TimestampMixin):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_member_ws_user"),
        {"schema": "workspace"},
    )
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspace.workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # admin|manager|collaborator|guest
    status: Mapped[str] = mapped_column(String(20), default="active")


# --------------------------------------------------------------------------- projects
class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    __table_args__ = {"schema": "projects"}
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspace.workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    client_name: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="active")
    owner_membership_id: Mapped[uuid.UUID | None] = mapped_column(UUIDpk)


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = {"schema": "projects"}
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.projects.id", ondelete="CASCADE"), primary_key=True
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUIDpk, nullable=False)
    project_role: Mapped[str] = mapped_column(String(20), default="member")


class ProjectAgent(Base):
    __tablename__ = "project_agents"
    __table_args__ = {"schema": "projects"}
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.projects.id", ondelete="CASCADE"), primary_key=True
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUIDpk, nullable=False)


# ------------------------------------------------------------------------------ tasks
class Task(Base, TimestampMixin):
    __tablename__ = "tasks"
    __table_args__ = {"schema": "tasks"}
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspace.workspaces.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="todo")
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assignee_kind: Mapped[str | None] = mapped_column(String(10))  # user|agent
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(UUIDpk)
    created_by_kind: Mapped[str] = mapped_column(String(10), default="user")
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(UUIDpk)
    board_order: Mapped[int] = mapped_column(Integer, default=0)


class TaskComment(Base):
    __tablename__ = "task_comments"
    __table_args__ = {"schema": "tasks"}
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUIDpk, nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.tasks.id", ondelete="CASCADE"), nullable=False
    )
    author_kind: Mapped[str] = mapped_column(String(10), default="user")
    author_id: Mapped[uuid.UUID | None] = mapped_column(UUIDpk)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ------------------------------------------------------------------------------- chat
class Room(Base, TimestampMixin):
    __tablename__ = "rooms"
    __table_args__ = {"schema": "chat"}
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspace.workspaces.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.projects.id", ondelete="CASCADE")
    )
    type: Mapped[str] = mapped_column(String(20), default="public_channel")
    name: Mapped[str | None] = mapped_column(String(200))
    topic: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUIDpk)


class Participant(Base):
    __tablename__ = "participants"
    __table_args__ = {"schema": "chat"}
    room_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat.rooms.id", ondelete="CASCADE"), primary_key=True
    )
    member_kind: Mapped[str] = mapped_column(String(10), primary_key=True)  # user|agent
    member_id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUIDpk, nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="member")
    last_read_message_id: Mapped[uuid.UUID | None] = mapped_column(UUIDpk)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = {"schema": "chat"}
    # busca server defaults (created_at) via RETURNING — evita lazy-load async após flush
    __mapper_args__ = {"eager_defaults": True}
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspace.workspaces.id", ondelete="CASCADE"), nullable=False
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat.rooms.id", ondelete="CASCADE"), nullable=False
    )
    author_kind: Mapped[str] = mapped_column(String(10), default="user")
    author_id: Mapped[uuid.UUID | None] = mapped_column(UUIDpk)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUIDpk)
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(UUIDpk)
    mentions: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# -------------------------------------------------------------------------- knowledge
class Document(Base, TimestampMixin):
    __tablename__ = "documents"
    __table_args__ = {"schema": "knowledge"}
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspace.workspaces.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUIDpk)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    mime: Mapped[str | None] = mapped_column(String(120))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(UUIDpk)


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = {"schema": "knowledge"}
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspace.workspaces.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge.documents.id", ondelete="CASCADE"), nullable=False
    )
    ord: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.embed_dim))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ----------------------------------------------------------------------------- agents
class Agent(Base, TimestampMixin):
    __tablename__ = "agents"
    __table_args__ = {"schema": "agents"}
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspace.workspaces.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(30), default="custom")
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    persona: Mapped[str | None] = mapped_column(Text)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(80), default="qwen3:8b")
    temperature: Mapped[float] = mapped_column(Numeric(3, 2), default=0.2)
    tools: Mapped[list] = mapped_column(JSONB, default=list)  # ["search_kb","create_task",...]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    appearance: Mapped[dict] = mapped_column(JSONB, default=dict)  # customização do hamster


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = {"schema": "agents"}
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspace.workspaces.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.agents.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUIDpk)
    trigger_kind: Mapped[str] = mapped_column(String(20), default="chat_mention")
    trigger_ref: Mapped[uuid.UUID | None] = mapped_column(UUIDpk)
    room_id: Mapped[uuid.UUID | None] = mapped_column(UUIDpk)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    model: Mapped[str] = mapped_column(String(80), default="qwen3:8b")
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Numeric(12, 6), default=0)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    output: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# -------------------------------------------------------------------------- approvals
class ApprovalRequest(Base, TimestampMixin):
    __tablename__ = "requests"
    __table_args__ = {"schema": "approvals"}
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspace.workspaces.id", ondelete="CASCADE"), nullable=False
    )
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(UUIDpk)
    requested_by_agent_id: Mapped[uuid.UUID | None] = mapped_column(UUIDpk)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    decided_by: Mapped[uuid.UUID | None] = mapped_column(UUIDpk)
    reason: Mapped[str | None] = mapped_column(Text)


# ------------------------------------------------------------------------------ audit
class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = {"schema": "audit"}
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUIDpk)
    type: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_kind: Mapped[str] = mapped_column(String(10), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUIDpk)
    target_kind: Mapped[str | None] = mapped_column(String(40))
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUIDpk)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class UsageDaily(Base):
    __tablename__ = "usage_daily"
    __table_args__ = {"schema": "audit"}
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Numeric(14, 6), default=0)
    run_count: Mapped[int] = mapped_column(Integer, default=0)


# ----------------------------------------------------------------------------- office
class OfficeScene(Base, TimestampMixin):
    __tablename__ = "scenes"
    __table_args__ = {"schema": "office"}
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspace.workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), default="Escritório")
    grid_width: Mapped[int] = mapped_column(Integer, default=14)
    grid_height: Mapped[int] = mapped_column(Integer, default=10)
    theme: Mapped[str] = mapped_column(String(40), default="classic")


class FurnitureCatalog(Base):
    """Catálogo global de móveis (sem tenant; sem RLS)."""

    __tablename__ = "furniture_catalog"
    __table_args__ = {"schema": "office"}
    code: Mapped[str] = mapped_column(String(60), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    width: Mapped[int] = mapped_column(Integer, default=1)
    depth: Mapped[int] = mapped_column(Integer, default=1)
    color: Mapped[str] = mapped_column(String(20), default="#b08968")
    icon: Mapped[str] = mapped_column(String(8), default="📦")
    walkable: Mapped[bool] = mapped_column(Boolean, default=False)


class FurniturePlacement(Base):
    __tablename__ = "furniture_placements"
    __table_args__ = {"schema": "office"}
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspace.workspaces.id", ondelete="CASCADE"), nullable=False
    )
    scene_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("office.scenes.id", ondelete="CASCADE"), nullable=False
    )
    furniture_code: Mapped[str] = mapped_column(
        ForeignKey("office.furniture_catalog.code"), nullable=False
    )
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)
    rotation: Mapped[int] = mapped_column(Integer, default=0)
    z_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Avatar(Base, TimestampMixin):
    __tablename__ = "avatars"
    __table_args__ = (
        UniqueConstraint("workspace_id", "owner_kind", "owner_id", name="uq_avatar_owner"),
        {"schema": "office"},
    )
    id: Mapped[uuid.UUID] = mapped_column(UUIDpk, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspace.workspaces.id", ondelete="CASCADE"), nullable=False
    )
    owner_kind: Mapped[str] = mapped_column(String(10), nullable=False)  # user|agent
    owner_id: Mapped[uuid.UUID] = mapped_column(UUIDpk, nullable=False)
    appearance: Mapped[dict] = mapped_column(JSONB, default=dict)
    home_x: Mapped[int] = mapped_column(Integer, default=0)
    home_y: Mapped[int] = mapped_column(Integer, default=0)


# Schemas necessários (criados pelo bootstrap antes do create_all)
ALL_SCHEMAS = [
    "auth",
    "workspace",
    "projects",
    "tasks",
    "chat",
    "knowledge",
    "agents",
    "approvals",
    "audit",
    "office",
]

# Tabelas de negócio com workspace_id → recebem RLS no bootstrap
TENANT_TABLES = [
    "projects.projects",
    "projects.project_members",
    "projects.project_agents",
    "tasks.tasks",
    "tasks.task_comments",
    "chat.rooms",
    "chat.participants",
    "chat.messages",
    "knowledge.documents",
    "knowledge.chunks",
    "agents.agents",
    "agents.agent_runs",
    "approvals.requests",
    "office.scenes",
    "office.furniture_placements",
    "office.avatars",
]
