from fastapi import Depends, Header, HTTPException, status

from app.auth.jwt import decode_token
from app.auth.models import AuthUser
from app.core.config import settings


def get_current_user(authorization: str | None = Header(default=None)) -> AuthUser:
    if not settings.auth_enabled:
        return AuthUser(sub="anonymous", email=None, roles=["admin"])

    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")

    return decode_token(token)


def require_roles(*allowed: str):
    def _dep(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if not allowed:
            return user
        user_roles = set(user.roles or [])
        if user_roles.intersection(set(allowed)):
            return user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return _dep

