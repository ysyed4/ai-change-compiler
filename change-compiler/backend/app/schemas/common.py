from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ChangeTarget(BaseModel):
    type: str
    id: str


class ChangeResponse(BaseModel):
    change_id: UUID
    status: str


class DecisionConstraintResponse(BaseModel):
    risk_score: int
    decision: str
    explanation: list[str]
    constraints: list[str]


class TimelineEvent(BaseModel):
    id: UUID
    event_type: str
    stage: str
    payload: dict
    created_at: datetime
