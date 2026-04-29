from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import AuthUser, require_roles
from app.db.session import get_db
from app.models.enums import EnforcementType
from app.models.policy import Policy
from app.schemas.policy import PolicyCreate, PolicyRead, PolicyUpdate
from app.services.safe_expr import UnsafeExpressionError, compile_expr


router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("", response_model=list[PolicyRead])
def list_policies(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("viewer", "approver", "executor", "requester", "admin")),
) -> list[Policy]:
    user_org = user.org_id or "default-org"
    return list(
        db.execute(select(Policy).where(Policy.org_id == user_org).order_by(Policy.created_at.desc())).scalars().all()
    )


@router.post("", response_model=PolicyRead)
def create_policy(
    payload: PolicyCreate,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("admin")),
) -> Policy:
    try:
        compile_expr(payload.condition_expr)
    except UnsafeExpressionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    policy = Policy(
        name=payload.name,
        description=payload.description,
        condition_expr=payload.condition_expr,
        enforcement=EnforcementType(payload.enforcement),
        enabled=payload.enabled,
        scope_platform=payload.scope_platform,
        scope_change_type=payload.scope_change_type,
        org_id=user.org_id or "default-org",
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/{policy_id}", response_model=PolicyRead)
def get_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("viewer", "approver", "executor", "requester", "admin")),
) -> Policy:
    policy = db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    if policy.org_id != (user.org_id or "default-org") and "admin" not in (user.roles or []):
        raise HTTPException(status_code=403, detail="Cross-organization access denied")
    return policy


@router.patch("/{policy_id}", response_model=PolicyRead)
def update_policy(
    policy_id: str,
    payload: PolicyUpdate,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("admin")),
) -> Policy:
    policy = db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    if policy.org_id != (user.org_id or "default-org"):
        raise HTTPException(status_code=403, detail="Cross-organization access denied")

    if payload.condition_expr is not None:
        try:
            compile_expr(payload.condition_expr)
        except UnsafeExpressionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        policy.condition_expr = payload.condition_expr

    if payload.description is not None:
        policy.description = payload.description
    if payload.enforcement is not None:
        policy.enforcement = EnforcementType(payload.enforcement)
    if payload.enabled is not None:
        policy.enabled = payload.enabled
    if payload.scope_platform is not None:
        policy.scope_platform = payload.scope_platform
    if payload.scope_change_type is not None:
        policy.scope_change_type = payload.scope_change_type

    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.post("/{policy_id}/version", response_model=PolicyRead)
def create_new_version(
    policy_id: str,
    payload: PolicyUpdate,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("admin")),
) -> Policy:
    base = db.get(Policy, policy_id)
    if not base:
        raise HTTPException(status_code=404, detail="Policy not found")

    new_condition = payload.condition_expr if payload.condition_expr is not None else base.condition_expr
    try:
        compile_expr(new_condition)
    except UnsafeExpressionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    next_version = int((base.version or 1) + 1)
    new_name = f"{base.name}-v{next_version}"

    policy = Policy(
        name=new_name,
        description=payload.description if payload.description is not None else base.description,
        condition_expr=new_condition,
        enforcement=EnforcementType(payload.enforcement) if payload.enforcement is not None else base.enforcement,
        enabled=payload.enabled if payload.enabled is not None else base.enabled,
        scope_platform=payload.scope_platform if payload.scope_platform is not None else base.scope_platform,
        scope_change_type=payload.scope_change_type if payload.scope_change_type is not None else base.scope_change_type,
        version=next_version,
        supersedes_policy_id=base.id,
        org_id=base.org_id,
    )
    db.add(policy)

    # Optional: disable prior version to reduce ambiguity during pilots.
    base.enabled = False
    db.add(base)

    db.commit()
    db.refresh(policy)
    return policy

