from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.changes import router as changes_router
from app.api.v1.policies import router as policies_router
from app.api.v1.reports import router as reports_router
from app.auth.jwt import issue_dev_token
from app.core.config import settings
from app.db.session import SessionLocal

app = FastAPI(title=settings.project_name)
app.include_router(changes_router, prefix=settings.api_v1_prefix)
app.include_router(policies_router, prefix=settings.api_v1_prefix)
app.include_router(reports_router, prefix=settings.api_v1_prefix)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/auth/token")
def dev_issue_token(payload: dict) -> dict[str, str]:
    """
    Dev-only token issuer for demos and local testing.
    In production, replace with OIDC or your identity provider.
    """
    if not settings.dev_token_endpoint_enabled:
        raise HTTPException(status_code=404, detail="Not found")

    sub = str(payload.get("sub") or payload.get("email") or "demo-user")
    email = payload.get("email")
    roles = payload.get("roles") or ["requester"]
    org_id = str(payload.get("org_id") or "default-org")
    if not isinstance(roles, list):
        roles = [str(roles)]

    token = issue_dev_token(sub=sub, email=email, roles=[str(r) for r in roles], org_id=org_id)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    finally:
        db.close()
    return {"status": "ready"}
