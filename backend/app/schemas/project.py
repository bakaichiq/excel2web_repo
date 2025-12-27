from pydantic import BaseModel

class ProjectCreate(BaseModel):
    code: str
    name: str
    description: str | None = None


class ProjectUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None

class ProjectOut(BaseModel):
    id: int
    code: str
    name: str
    description: str | None = None
