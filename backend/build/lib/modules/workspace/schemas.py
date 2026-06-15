from pydantic import BaseModel, EmailStr


class WorkspaceCreate(BaseModel):
    name: str
    slug: str


class WorkspaceOut(BaseModel):
    id: str
    slug: str
    name: str
    plan: str
    role: str | None = None


class MemberOut(BaseModel):
    membership_id: str
    user_id: str
    name: str
    email: str
    role: str
    status: str


class MemberAdd(BaseModel):
    email: EmailStr
    role: str = "collaborator"


class RoleChange(BaseModel):
    role: str


class SettingsOut(BaseModel):
    default_model: str
    monthly_token_budget: int | None
    office_theme: str
