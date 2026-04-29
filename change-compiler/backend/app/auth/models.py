from pydantic import BaseModel


class AuthUser(BaseModel):
    sub: str
    email: str | None = None
    roles: list[str] = []
    org_id: str | None = None

