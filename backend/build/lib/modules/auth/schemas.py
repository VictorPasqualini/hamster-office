from pydantic import BaseModel, EmailStr


class RegisterIn(BaseModel):
    email: EmailStr
    name: str
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class WorkspaceBrief(BaseModel):
    id: str
    slug: str
    name: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    workspaces: list[WorkspaceBrief] = []


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    avatar_url: str | None = None


class MeOut(BaseModel):
    user: UserOut
    workspaces: list[WorkspaceBrief]
