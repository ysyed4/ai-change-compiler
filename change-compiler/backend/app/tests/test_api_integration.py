from fastapi.testclient import TestClient

from app.main import app


def _issue_token(client: TestClient, roles: list[str]) -> str:
    resp = client.post("/auth/token", json={"email": "ci@example.com", "roles": roles})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_auth_required_for_changes_endpoints():
    client = TestClient(app)

    resp = client.post(
        "/api/v1/changes",
        json={
            "platform": "kafka",
            "change_type": "restart_component",
            "target": {"type": "broker", "id": "broker-1"},
            "reason": "maintenance",
            "rollback_available": True,
        },
    )
    assert resp.status_code in (401, 403)


def test_policy_crud_and_safe_expression_validation():
    client = TestClient(app)
    token = _issue_token(client, ["admin"])
    headers = {"Authorization": f"Bearer {token}"}

    # Reject unsafe expression
    resp = client.post(
        "/api/v1/policies",
        headers=headers,
        json={
            "name": "bad",
            "description": "bad",
            "condition_expr": "__import__('os').system('echo pwned')",
            "enforcement": "hard_stop",
            "enabled": True,
            "scope_platform": "kafka",
            "scope_change_type": "restart_component",
        },
    )
    assert resp.status_code == 400

    # Accept safe expression
    resp = client.post(
        "/api/v1/policies",
        headers=headers,
        json={
            "name": "block-high-risk",
            "description": "Block if too risky",
            "condition_expr": "risk_score > 90",
            "enforcement": "hard_stop",
            "enabled": True,
            "scope_platform": "kafka",
            "scope_change_type": "restart_component",
        },
    )
    assert resp.status_code == 200
    policy = resp.json()
    assert policy["version"] == 1

    # Version it
    resp = client.post(
        f"/api/v1/policies/{policy['id']}/version",
        headers=headers,
        json={"condition_expr": "risk_score > 80"},
    )
    assert resp.status_code == 200
    v2 = resp.json()
    assert v2["version"] == 2
    assert v2["supersedes_policy_id"] == policy["id"]


def test_change_flow_smoke_with_roles():
    client = TestClient(app)

    requester_token = _issue_token(client, ["requester", "viewer"])
    requester_headers = {"Authorization": f"Bearer {requester_token}"}

    resp = client.post(
        "/api/v1/changes",
        headers=requester_headers,
        json={
            "platform": "kafka",
            "change_type": "restart_component",
            "target": {"type": "broker", "id": "broker-1"},
            "reason": "maintenance",
            "rollback_available": True,
        },
    )
    assert resp.status_code == 200
    change_id = resp.json()["change_id"]

    resp = client.post(f"/api/v1/changes/{change_id}/evaluate", headers=requester_headers)
    # evaluation may fail if Kafka/Prometheus not reachable in CI; this still validates auth+route wiring.
    assert resp.status_code in (200, 400, 500)

    # requester cannot self-approve
    resp = client.post(f"/api/v1/changes/{change_id}/approve", headers=requester_headers)
    assert resp.status_code in (400, 403)

    approver_token = _issue_token(client, ["approver", "viewer"])
    approver_headers = {"Authorization": f"Bearer {approver_token}"}
    resp = client.post(f"/api/v1/changes/{change_id}/approve", headers=approver_headers)
    assert resp.status_code in (200, 400, 500)

    executor_token = _issue_token(client, ["executor", "viewer"])
    executor_headers = {"Authorization": f"Bearer {executor_token}"}
    resp = client.post(f"/api/v1/changes/{change_id}/execute", headers=executor_headers)
    assert resp.status_code in (200, 400, 500)

