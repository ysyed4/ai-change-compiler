from fastapi.testclient import TestClient

from app.main import app


def _issue_token(client: TestClient, email: str, roles: list[str]) -> str:
    resp = client.post("/auth/token", json={"email": email, "roles": roles, "org_id": "default-org"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_contract_unsafe_policy_rejected():
    client = TestClient(app)
    admin = _issue_token(client, "admin@contracts.local", ["admin"])
    headers = {"Authorization": f"Bearer {admin}"}
    resp = client.post(
        "/api/v1/policies",
        headers=headers,
        json={
            "name": "contract-unsafe",
            "description": "contract unsafe",
            "condition_expr": "__import__('os').system('echo pwned')",
            "enforcement": "hard_stop",
            "enabled": True,
            "scope_platform": "kafka",
            "scope_change_type": "restart_component",
        },
    )
    assert resp.status_code == 400


def test_contract_requester_cannot_self_approve():
    client = TestClient(app)
    dual = _issue_token(client, "dual@contracts.local", ["requester", "approver", "viewer"])
    headers = {"Authorization": f"Bearer {dual}"}

    submit = client.post(
        "/api/v1/changes",
        headers=headers,
        json={
            "platform": "kafka",
            "change_type": "restart_component",
            "target": {"type": "broker", "id": "broker-1"},
            "reason": "contract test",
            "org_id": "default-org",
            "rollback_available": True,
        },
    )
    assert submit.status_code == 200
    change_id = submit.json()["change_id"]

    _ = client.post(f"/api/v1/changes/{change_id}/evaluate", headers=headers)
    approve = client.post(f"/api/v1/changes/{change_id}/approve", headers=headers)
    assert approve.status_code == 400
    assert "cannot approve" in approve.json().get("detail", "").lower()

