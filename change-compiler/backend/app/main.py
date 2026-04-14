from fastapi import FastAPI
from sqlalchemy import text

from app.api.v1.changes import router as changes_router
from app.core.config import settings
from app.db.session import SessionLocal

app = FastAPI(title=settings.project_name)
app.include_router(changes_router, prefix=settings.api_v1_prefix)


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
