from pydantic import BaseModel


class RoomCreate(BaseModel):
    type: str = "public_channel"  # public_channel|private_channel|direct|human_agent
    name: str | None = None
    topic: str | None = None
    project_id: str | None = None
    agent_ids: list[str] = []  # agentes participantes (para human_agent)


class RoomOut(BaseModel):
    id: str
    type: str
    name: str | None
    topic: str | None
    project_id: str | None


class MessageSend(BaseModel):
    content: str
    parent_id: str | None = None
