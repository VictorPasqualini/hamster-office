from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    client_name: str | None = None
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    client_name: str | None = None
    description: str | None = None
    status: str | None = None


class ProjectOut(BaseModel):
    id: str
    name: str
    client_name: str | None
    description: str | None
    status: str


class AgentAssign(BaseModel):
    agent_id: str
