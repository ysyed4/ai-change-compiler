from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ChangeTarget, ORMBase


class ChangeRequestCreate(BaseModel):
    platform: str = "kafka"
    change_type: str = "restart_component"
    target: ChangeTarget
    reason: str
    requested_by: str | None = None
    org_id: str = "default-org"
    rollback_available: bool = True


class ChangeRequestRead(ORMBase):
    id: UUID
    platform: str
    change_type: str
    target_type: str
    target_id: str
    reason: str
    status: str
    requested_by: str
    org_id: str
    requested_time: datetime
    requires_manual_approval: bool
    approved_by: str | None = None
    approved_at: datetime | None = None
    decision: str | None = None
    risk_score: int | None = None
    explanations: list[str]
    constraints: list[str]
    created_at: datetime
    updated_at: datetime


class ChangeEvaluationResponse(BaseModel):
    change_id: UUID
    decision: str
    risk_score: int
    explanation: list[str]
    constraints: list[str]
    telemetry_source_status: str
    metadata_source_status: str


class ChangeExecuteResponse(BaseModel):
    change_id: UUID
    status: str
    execution_mode: str


class ChangeApproveResponse(BaseModel):
    change_id: UUID
    status: str
    approved_by: str
