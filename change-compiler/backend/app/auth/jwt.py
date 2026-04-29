from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status

from app.auth.models import AuthUser
from app.core.config import settings


def issue_dev_token(*, sub: str, email: str | None, roles: list[str], org_id: str = "default-org", ttl_minutes: int = 60) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ttl_minutes)).timestamp()),
        "sub": sub,
        "email": email,
        "roles": roles,
        "org_id": org_id,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> AuthUser:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
    except jwt.PyJWTError as exc:  # type: ignore[attr-defined]
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    return AuthUser(
        sub=str(payload.get("sub")),
        email=payload.get("email"),
        roles=list(payload.get("roles") or []),
        org_id=payload.get("org_id"),
    )

