from datetime import datetime, timezone
from uuid import uuid4

from app.api.v1 import changes as change_routes
from app.models.audit_log import AuditLog
from app.models.change_request import ChangeRequest
from app.models.enums import ChangeStatus
from app.schemas.change_request import ChangeEvaluationResponse
from app.services.kafka_adapter import AdapterCollectionResult, KafkaMetadataSnapshot, KafkaTelemetrySnapshot


class FakeScalarResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items

    def __iter__(self):
        return iter(self._items)


class FakeExecuteResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return FakeScalarResult(self._items)


class FakeSession:
    def __init__(self, change: ChangeRequest):
        self.change = change
        self.audit_logs: list[AuditLog] = []

    def get(self, model, change_id):
        if model is ChangeRequest and self.change.id == change_id:
            return self.change
        return None

    def execute(self, stmt):
        _ = stmt
        return FakeExecuteResult([])

    def add(self, item):
        if isinstance(item, AuditLog):
            self.audit_logs.append(item)

    def commit(self):
        return None


class StubAdapter:
    def __init__(self, result: AdapterCollectionResult):
        self.result = result

    def collect_cluster_state(self, target_id: str):
        _ = target_id
        return self.result


def make_change(target_id: str = "broker-1") -> ChangeRequest:
    return ChangeRequest(
        id=uuid4(),
        platform="kafka",
        change_type="restart_component",
        target_type="broker",
        target_id=target_id,
        reason="maintenance",
        status=ChangeStatus.received,
        requested_by="tester",
        requested_time=datetime.now(timezone.utc),
        rollback_available=True,
        explanations=[],
        constraints=[],
    )


def make_result(*, broker_exists=True, offline_partitions=0, telemetry_status="real", metadata_status="real"):
    return AdapterCollectionResult(
        telemetry=KafkaTelemetrySnapshot(
            offline_partitions=offline_partitions,
            under_replicated_partitions=0,
            consumer_lag=10,
            broker_disk_usage_percent=50,
            controller_change_rate=0,
        ),
        telemetry_source_status=telemetry_status,
        telemetry_errors=["telemetry unavailable"] if telemetry_status == "fallback" else [],
        metadata=KafkaMetadataSnapshot(
            broker_ids=[1, 2, 3] if broker_exists else [2, 3],
            broker_exists=broker_exists,
            topic_count=3,
            partition_count=12,
            leader_partitions_on_target=2 if broker_exists else 0,
        ),
        metadata_source_status=metadata_status,
        metadata_errors=["metadata unavailable"] if metadata_status == "fallback" else [],
    )


def test_healthy_restart_evaluation(monkeypatch):
    change = make_change("broker-1")
    db = FakeSession(change)

    monkeypatch.setattr(change_routes, "_adapter", lambda: StubAdapter(make_result()))

    response = change_routes.evaluate_change(change.id, db)

    assert isinstance(response, ChangeEvaluationResponse)
    assert response.decision == "allow_with_constraints"
    assert response.telemetry_source_status == "real"
    assert response.metadata_source_status == "real"
    assert len(db.audit_logs) == 1


def test_blocked_broker_does_not_exist(monkeypatch):
    change = make_change("broker-9")
    db = FakeSession(change)

    monkeypatch.setattr(change_routes, "_adapter", lambda: StubAdapter(make_result(broker_exists=False)))

    response = change_routes.evaluate_change(change.id, db)

    assert response.decision == "block"
    assert any("does not exist" in msg for msg in response.explanation)


def test_blocked_offline_partitions(monkeypatch):
    change = make_change()
    db = FakeSession(change)

    monkeypatch.setattr(change_routes, "_adapter", lambda: StubAdapter(make_result(offline_partitions=2)))

    response = change_routes.evaluate_change(change.id, db)

    assert response.decision == "block"
    assert any("offline partitions" in msg.lower() for msg in response.explanation)


def test_blocked_telemetry_unavailable(monkeypatch):
    change = make_change()
    db = FakeSession(change)

    monkeypatch.setattr(
        change_routes,
        "_adapter",
        lambda: StubAdapter(make_result(telemetry_status="fallback", metadata_status="fallback")),
    )

    response = change_routes.evaluate_change(change.id, db)

    assert response.decision == "block"
    assert response.telemetry_source_status == "fallback"


def test_allow_with_constraints_partial_data(monkeypatch):
    change = make_change()
    db = FakeSession(change)

    monkeypatch.setattr(
        change_routes,
        "_adapter",
        lambda: StubAdapter(make_result(telemetry_status="partial", metadata_status="real")),
    )

    response = change_routes.evaluate_change(change.id, db)

    assert response.decision == "allow_with_constraints"
    assert len(response.constraints) > 0
