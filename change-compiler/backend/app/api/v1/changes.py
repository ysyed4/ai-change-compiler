from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.change_request import ChangeRequest
from app.models.enums import ChangeStatus, DecisionType
from app.models.policy import Policy
from app.schemas.change_request import (
    ChangeEvaluationResponse,
    ChangeExecuteResponse,
    ChangeRequestCreate,
    ChangeRequestRead,
)
from app.schemas.common import ChangeResponse
from app.services.executor import GuardedExecutor
from app.services.kafka_adapter import KafkaAdapter
from app.services.policy_compiler import PolicyCompiler
from app.services.prometheus_client import PrometheusClient
from app.services.rules_engine import RulesEngine

router = APIRouter(prefix="/changes", tags=["changes"])


def _adapter() -> KafkaAdapter:
    prometheus = PrometheusClient(
        base_url=settings.prometheus_url,
        timeout_seconds=settings.prometheus_timeout_seconds,
    )
    return KafkaAdapter(
        prometheus_client=prometheus,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        metadata_timeout_seconds=settings.kafka_metadata_timeout_seconds,
    )


def _log_event(
    db: Session,
    change_request_id: UUID,
    event_type: str,
    stage: str,
    payload: dict,
    telemetry_snapshot: dict | None = None,
    rule_hits: list[dict] | None = None,
    policy_hits: list[dict] | None = None,
) -> None:
    db.add(
        AuditLog(
            change_request_id=change_request_id,
            event_type=event_type,
            stage=stage,
            payload=payload,
            telemetry_snapshot=telemetry_snapshot or {},
            rule_hits=rule_hits or [],
            policy_hits=policy_hits or [],
        )
    )


def _evaluate_change(change: ChangeRequest, db: Session) -> tuple[ChangeEvaluationResponse, list[dict], dict]:
    adapter = _adapter()
    cluster_state = adapter.collect_cluster_state(change.target_id)

    rules = RulesEngine().evaluate(
        telemetry=cluster_state.telemetry,
        metadata=cluster_state.metadata,
        telemetry_source_status=cluster_state.telemetry_source_status,
        metadata_source_status=cluster_state.metadata_source_status,
        telemetry_errors=cluster_state.telemetry_errors,
        metadata_errors=cluster_state.metadata_errors,
    )

    policies = db.execute(
        select(Policy).where(
            Policy.enabled.is_(True),
            Policy.scope_platform == change.platform,
            Policy.scope_change_type == change.change_type,
        )
    ).scalars().all()

    policy_result = PolicyCompiler().evaluate(
        policies,
        context={
            "risk_score": rules.risk_score,
            "offline_partitions": cluster_state.telemetry.offline_partitions,
            "under_replicated_partitions": cluster_state.telemetry.under_replicated_partitions,
            "consumer_lag": cluster_state.telemetry.consumer_lag,
            "broker_disk_usage_percent": cluster_state.telemetry.broker_disk_usage_percent,
        },
    )

    decision = rules.decision
    if policy_result.decision_override:
        decision = policy_result.decision_override

    constraints = [*rules.constraints, *policy_result.constraints]
    explanations = [*rules.explanations, *policy_result.explanations]

    change.status = ChangeStatus.blocked if decision == DecisionType.block.value else ChangeStatus.evaluated
    change.decision = DecisionType(decision)
    change.risk_score = rules.risk_score
    change.explanations = explanations
    change.constraints = constraints

    telemetry_snapshot = {
        "offline_partitions": cluster_state.telemetry.offline_partitions,
        "under_replicated_partitions": cluster_state.telemetry.under_replicated_partitions,
        "consumer_lag": cluster_state.telemetry.consumer_lag,
        "broker_disk_usage_percent": cluster_state.telemetry.broker_disk_usage_percent,
        "controller_change_rate": cluster_state.telemetry.controller_change_rate,
        "telemetry_source_status": cluster_state.telemetry_source_status,
        "metadata_source_status": cluster_state.metadata_source_status,
        "metadata": {
            "broker_ids": cluster_state.metadata.broker_ids,
            "broker_exists": cluster_state.metadata.broker_exists,
            "topic_count": cluster_state.metadata.topic_count,
            "partition_count": cluster_state.metadata.partition_count,
            "leader_partitions_on_target": cluster_state.metadata.leader_partitions_on_target,
        },
        "telemetry_errors": cluster_state.telemetry_errors,
        "metadata_errors": cluster_state.metadata_errors,
    }

    response = ChangeEvaluationResponse(
        change_id=change.id,
        decision=decision,
        risk_score=rules.risk_score,
        explanation=explanations,
        constraints=constraints,
        telemetry_source_status=cluster_state.telemetry_source_status,
        metadata_source_status=cluster_state.metadata_source_status,
    )

    return response, rules.rule_hits, telemetry_snapshot


@router.post("", response_model=ChangeResponse)
def submit_change(payload: ChangeRequestCreate, db: Session = Depends(get_db)) -> ChangeResponse:
    change = ChangeRequest(
        platform=payload.platform,
        change_type=payload.change_type,
        target_type=payload.target.type,
        target_id=payload.target.id,
        reason=payload.reason,
        requested_by=payload.requested_by,
        rollback_available=payload.rollback_available,
        status=ChangeStatus.received,
    )
    db.add(change)
    db.flush()

    _log_event(
        db,
        change_request_id=change.id,
        event_type="change_submitted",
        stage="intake",
        payload={"reason": payload.reason, "target": payload.target.id},
    )
    db.commit()

    return ChangeResponse(change_id=change.id, status=change.status.value)


@router.get("/{change_id}", response_model=ChangeRequestRead)
def get_change(change_id: UUID, db: Session = Depends(get_db)) -> ChangeRequest:
    change = db.get(ChangeRequest, change_id)
    if not change:
        raise HTTPException(status_code=404, detail="Change request not found")
    return change


@router.get("/{change_id}/audit")
def get_change_audit(change_id: UUID, db: Session = Depends(get_db)) -> list[dict]:
    change = db.get(ChangeRequest, change_id)
    if not change:
        raise HTTPException(status_code=404, detail="Change request not found")

    events = db.execute(
        select(AuditLog).where(AuditLog.change_request_id == change_id).order_by(AuditLog.created_at.asc())
    ).scalars()
    return [
        {
            "id": str(event.id),
            "event_type": event.event_type,
            "stage": event.stage,
            "payload": event.payload,
            "telemetry_snapshot": event.telemetry_snapshot,
            "rule_hits": event.rule_hits,
            "policy_hits": event.policy_hits,
            "created_at": event.created_at.isoformat(),
        }
        for event in events
    ]


@router.post("/{change_id}/evaluate", response_model=ChangeEvaluationResponse)
def evaluate_change(change_id: UUID, db: Session = Depends(get_db)) -> ChangeEvaluationResponse:
    change = db.get(ChangeRequest, change_id)
    if not change:
        raise HTTPException(status_code=404, detail="Change request not found")

    evaluation_response, rule_hits, telemetry_snapshot = _evaluate_change(change, db)

    _log_event(
        db,
        change_request_id=change.id,
        event_type="change_evaluated",
        stage="evaluation",
        payload={
            "decision": evaluation_response.decision,
            "risk_score": evaluation_response.risk_score,
            "telemetry_source_status": evaluation_response.telemetry_source_status,
            "metadata_source_status": evaluation_response.metadata_source_status,
        },
        telemetry_snapshot=telemetry_snapshot,
        rule_hits=rule_hits,
        policy_hits=[],
    )
    db.commit()

    return evaluation_response


@router.post("/{change_id}/execute", response_model=ChangeExecuteResponse)
def execute_change(change_id: UUID, db: Session = Depends(get_db)) -> ChangeExecuteResponse:
    change = db.get(ChangeRequest, change_id)
    if not change:
        raise HTTPException(status_code=404, detail="Change request not found")

    if change.decision not in {DecisionType.allow, DecisionType.allow_with_constraints}:
        _log_event(
            db,
            change_request_id=change.id,
            event_type="execution_blocked",
            stage="execution",
            payload={"reason": "Change is not eligible for execution", "execution_mode": "blocked_before_action"},
        )
        db.commit()
        raise HTTPException(status_code=400, detail="Change is not eligible for execution")

    # Precondition verification at execution time.
    eval_response, _, _ = _evaluate_change(change, db)
    if eval_response.decision == DecisionType.block.value:
        change.status = ChangeStatus.blocked
        _log_event(
            db,
            change_request_id=change.id,
            event_type="execution_blocked",
            stage="precheck",
            payload={
                "reason": "Precondition check failed at execution time",
                "execution_mode": "blocked_before_action",
                "telemetry_source_status": eval_response.telemetry_source_status,
                "metadata_source_status": eval_response.metadata_source_status,
            },
        )
        db.commit()
        return ChangeExecuteResponse(
            change_id=change.id,
            status=change.status.value,
            execution_mode="blocked_before_action",
        )

    change.status = ChangeStatus.executing

    adapter = _adapter()
    cluster_state = adapter.collect_cluster_state(change.target_id)
    result = GuardedExecutor().execute_restart_workflow(
        cluster_state.telemetry,
        change.constraints,
        allow_real_restart=settings.execute_real_restart,
    )

    for step in result.steps:
        _log_event(
            db,
            change_request_id=change.id,
            event_type="execution_step",
            stage=step["stage"],
            payload=step,
            telemetry_snapshot={
                "telemetry_source_status": cluster_state.telemetry_source_status,
                "metadata_source_status": cluster_state.metadata_source_status,
            },
        )

    change.status = ChangeStatus(result.terminal_status)
    _log_event(
        db,
        change_request_id=change.id,
        event_type="execution_finished",
        stage="execution",
        payload={"status": change.status.value, "execution_mode": result.execution_mode},
    )

    db.commit()

    return ChangeExecuteResponse(
        change_id=change.id,
        status=change.status.value,
        execution_mode=result.execution_mode,
    )
