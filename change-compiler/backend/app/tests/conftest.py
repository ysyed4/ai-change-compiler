from collections.abc import Generator

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def clean_db(db_session: Session) -> None:
    """
    Keep integration tests isolated.
    Assumes Alembic migrations already created tables.
    """
    db_session.execute(text("TRUNCATE TABLE audit_logs RESTART IDENTITY CASCADE"))
    db_session.execute(text("TRUNCATE TABLE change_requests RESTART IDENTITY CASCADE"))
    db_session.execute(text("TRUNCATE TABLE policies RESTART IDENTITY CASCADE"))
    db_session.commit()

