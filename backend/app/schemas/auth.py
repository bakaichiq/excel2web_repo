from pydantic import BaseModel

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginIn(BaseModel):
    login: str
    password: str

class UserOut(BaseModel):
    id: int
    login: str
    full_name: str | None = None
    role: str
