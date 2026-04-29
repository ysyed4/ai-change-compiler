from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import AuthUser, require_roles
from app.db.session import get_db
from app.models.change_request import ChangeRequest
from app.models.enums import DecisionType
from app.services.runtime_metrics import metrics


router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/pilot-value")
def pilot_value_report(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("viewer", "approver", "executor", "admin")),
) -> dict:
    org_id = user.org_id or "default-org"
    changes = db.execute(select(ChangeRequest).where(ChangeRequest.org_id == org_id)).scalars().all()

    total_changes = len(changes)
    blocked = sum(1 for c in changes if c.decision == DecisionType.block)
    manual_approvals = sum(1 for c in changes if c.requires_manual_approval)
    approved = sum(1 for c in changes if c.approved_by is not None)

    lead_times = []
    for c in changes:
        if c.approved_at:
            lead_times.append((c.approved_at - c.requested_time).total_seconds())
    avg_approval_seconds = sum(lead_times) / len(lead_times) if lead_times else 0.0

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "org_id": org_id,
        "totals": {
            "total_changes": total_changes,
            "blocked_risky_changes": blocked,
            "requires_manual_approval": manual_approvals,
            "approved_changes": approved,
        },
        "timing": {
            "average_approval_seconds": round(avg_approval_seconds, 2),
        },
        "runtime_metrics": metrics.snapshot(),
    }

