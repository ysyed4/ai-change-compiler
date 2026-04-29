from datetime import datetime, timezone
from uuid import uuid4

from app.api.v1 import changes as change_routes
from app.models.audit_log import AuditLog
from app.models.change_request import ChangeRequest
from app.models.enums import ChangeStatus, DecisionType
from app.schemas.change_request import ChangeEvaluationResponse
from app.services.kafka_adapter import AdapterCollectionResult, KafkaMetadataSnapshot, KafkaTelemetrySnapshot


class FakeSession:
    def __init__(self, change: ChangeRequest):
        self.change = change
        self.audit_logs: list[AuditLog] = []

    def get(self, model, change_id):
        if model is ChangeRequest and self.change.id == change_id:
            return self.change
        return None

    def add(self, item):
        if isinstance(item, AuditLog):
            self.audit_logs.append(item)

    def commit(self):
        return None


def make_change() -> ChangeRequest:
    return ChangeRequest(
        id=uuid4(),
        platform="kafka",
        change_type="restart_component",
        target_type="broker",
        target_id="broker-1",
        reason="maintenance",
        status=ChangeStatus.evaluated,
        requested_by="tester",
        requested_time=datetime.now(timezone.utc),
        rollback_available=True,
        decision=DecisionType.allow_with_constraints,
        explanations=[],
        constraints=["one broker at a time"],
    )


class StubAdapter:
    def collect_cluster_state(self, target_id: str):
        _ = target_id
        return AdapterCollectionResult(
            telemetry=KafkaTelemetrySnapshot(
                offline_partitions=0,
                under_replicated_partitions=0,
                consumer_lag=10,
                broker_disk_usage_percent=50,
                controller_change_rate=0,
            ),
            telemetry_source_status="real",
            telemetry_errors=[],
            metadata=KafkaMetadataSnapshot(
                broker_ids=[1, 2, 3],
                broker_exists=True,
                topic_count=3,
                partition_count=12,
                leader_partitions_on_target=2,
            ),
            metadata_source_status="real",
            metadata_errors=[],
        )


def test_execute_flow_writes_audit_logs(monkeypatch):
    change = make_change()
    db = FakeSession(change)

    monkeypatch.setattr(change_routes, "_adapter", lambda: StubAdapter())
    monkeypatch.setattr(
        change_routes,
        "_evaluate_change",
        lambda current_change, current_db: (
            ChangeEvaluationResponse(
                change_id=current_change.id,
                decision="allow_with_constraints",
                risk_score=55,
                explanation=["safe enough"],
                constraints=["one at a time"],
                telemetry_source_status="real",
                metadata_source_status="real",
            ),
            [],
            [],
            {},
        ),
    )

    response = change_routes.execute_change(change.id, db)

    assert response.status == "completed"
    assert response.execution_mode == "simulated"
    assert len(db.audit_logs) >= 2
    assert any(event.event_type == "execution_finished" for event in db.audit_logs)
