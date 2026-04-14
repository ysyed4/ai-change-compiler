from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMBase


class PolicyCreate(BaseModel):
    name: str
    description: str
    condition_expr: str
    enforcement: str = "hard_stop"
    enabled: bool = True
    scope_platform: str = "kafka"
    scope_change_type: str = "restart_component"


class PolicyRead(ORMBase):
    id: UUID
    name: str
    description: str
    condition_expr: str
    enforcement: str
    enabled: bool
    scope_platform: str
    scope_change_type: str
    created_at: datetime
    updated_at: datetime


class PolicyEvaluationHit(BaseModel):
    policy_name: str
    enforcement: str
    matched: bool
    message: str
