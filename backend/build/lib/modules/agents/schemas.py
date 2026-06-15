from pydantic import BaseModel

AGENT_TYPES = {
    "commercial",
    "finance",
    "legal",
    "data_analyst",
    "developer",
    "support",
    "custom",
}
AVAILABLE_TOOLS = {"search_kb", "create_task", "update_task", "post_message", "generate_report"}


class AgentCreate(BaseModel):
    name: str
    type: str = "custom"
    persona: str | None = None
    system_prompt: str
    model: str = "qwen3:8b"
    temperature: float = 0.2
    tools: list[str] = []
    appearance: dict = {}


class AgentUpdate(BaseModel):
    name: str | None = None
    persona: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    temperature: float | None = None
    tools: list[str] | None = None
    is_active: bool | None = None
    appearance: dict | None = None


class AgentOut(BaseModel):
    id: str
    name: str
    type: str
    persona: str | None
    model: str
    temperature: float
    tools: list[str]
    is_active: bool
    appearance: dict


class ExecuteIn(BaseModel):
    prompt: str
    room_id: str | None = None
    project_id: str | None = None


class RunOut(BaseModel):
    id: str
    agent_id: str
    status: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    output: str | None
    error: str | None
