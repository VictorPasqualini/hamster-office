from pydantic import BaseModel


class UploadUrlIn(BaseModel):
    filename: str
    mime: str | None = None
    project_id: str | None = None
    title: str | None = None


class UploadUrlOut(BaseModel):
    document_id: str
    object_key: str
    upload_url: str


class DocumentOut(BaseModel):
    id: str
    title: str
    mime: str | None
    status: str
    project_id: str | None


class SearchIn(BaseModel):
    query: str
    top_k: int = 6
    project_id: str | None = None
