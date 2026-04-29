#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PATH = ROOT / "simulation" / "scenarios.json"
ARTIFACTS_DIR = ROOT / "simulation" / "artifacts"


@dataclass
class RoleTokens:
    requester: str
    approver: str
    executor: str
    admin: str
    dual: str
    viewer: str


class ScenarioRunner:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_v1 = f"{self.base_url}/api/v1"

    def _token(self, email: str, roles: list[str], org_id: str = "default-org") -> str:
        resp = requests.post(
            f"{self.base_url}/auth/token",
            json={"email": email, "roles": roles, "org_id": org_id},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def issue_tokens(self) -> RoleTokens:
        return RoleTokens(
            requester=self._token("requester@sim.local", ["requester", "viewer"]),
            approver=self._token("approver@sim.local", ["approver", "viewer"]),
            executor=self._token("executor@sim.local", ["executor", "viewer"]),
            admin=self._token("admin@sim.local", ["admin"]),
            dual=self._token("dual@sim.local", ["requester", "approver", "viewer"]),
            viewer=self._token("viewer@sim.local", ["viewer"]),
        )

    @staticmethod
    def _h(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def create_policy(self, token: str, policy: dict[str, Any], suffix: str) -> requests.Response:
        payload = {
            "name": f"{policy['name']}-{suffix}",
            "description": f"simulation policy {suffix}",
            "condition_expr": policy["condition_expr"],
            "enforcement": policy["enforcement"],
            "enabled": True,
            "scope_platform": "kafka",
            "scope_change_type": "restart_component",
        }
        return requests.post(
            f"{self.api_v1}/policies",
            json=payload,
            headers={**self._h(token), "Content-Type": "application/json"},
            timeout=30,
        )

    def disable_simulation_policies(self, token: str) -> None:
        listed = requests.get(f"{self.api_v1}/policies", headers=self._h(token), timeout=30)
        if listed.status_code != 200:
            return
        for pol in listed.json():
            name = str(pol.get("name", ""))
            if not name.startswith("sim-") and not name.startswith("unsafe-"):
                continue
            pid = pol.get("id")
            if not pid:
                continue
            _ = requests.patch(
                f"{self.api_v1}/policies/{pid}",
                headers={**self._h(token), "Content-Type": "application/json"},
                json={"enabled": False},
                timeout=30,
            )

    def run_change_flow(
        self,
        tokens: RoleTokens,
        target_id: str,
        enforce_manual: bool = False,
        run_separation_test: bool = False,
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        submit_payload = {
            "platform": "kafka",
            "change_type": "restart_component",
            "target": {"type": "broker", "id": target_id},
            "reason": "simulation run",
            "rollback_available": True,
            "org_id": "default-org",
        }
        submit_actor = tokens.dual if run_separation_test else tokens.requester
        submit = requests.post(f"{self.api_v1}/changes", json=submit_payload, headers=self._h(submit_actor), timeout=30)
        out["submit"] = {"status_code": submit.status_code, "body": submit.json() if submit.content else {}}
        if submit.status_code != 200:
            return out

        change_id = out["submit"]["body"]["change_id"]
        out["change_id"] = change_id

        evaluate = requests.post(
            f"{self.api_v1}/changes/{change_id}/evaluate",
            headers=self._h(tokens.requester),
            timeout=30,
        )
        out["evaluate"] = {"status_code": evaluate.status_code, "body": evaluate.json() if evaluate.content else {}}

        if run_separation_test:
            self_approve = requests.post(
                f"{self.api_v1}/changes/{change_id}/approve",
                headers=self._h(tokens.dual),
                timeout=30,
            )
            out["self_approve"] = {"status_code": self_approve.status_code, "body": self_approve.json() if self_approve.content else {}}
            return out

        if enforce_manual:
            approve = requests.post(
                f"{self.api_v1}/changes/{change_id}/approve",
                headers=self._h(tokens.approver),
                timeout=30,
            )
            out["approve"] = {"status_code": approve.status_code, "body": approve.json() if approve.content else {}}

        execute = requests.post(
            f"{self.api_v1}/changes/{change_id}/execute",
            headers=self._h(tokens.executor),
            timeout=30,
        )
        out["execute"] = {"status_code": execute.status_code, "body": execute.json() if execute.content else {}}

        audit = requests.get(
            f"{self.api_v1}/changes/{change_id}/audit",
            headers=self._h(tokens.requester),
            timeout=30,
        )
        audit_body = audit.json() if audit.content else []
        out["audit"] = {
            "status_code": audit.status_code,
            "count": len(audit_body) if isinstance(audit_body, list) else 0,
            "events": [e.get("event_type") for e in audit_body] if isinstance(audit_body, list) else [],
        }
        return out

    def get_report(self, token: str) -> dict[str, Any]:
        resp = requests.get(f"{self.api_v1}/reports/pilot-value", headers=self._h(token), timeout=30)
        return {"status_code": resp.status_code, "body": resp.json() if resp.content else {}}


def load_scenarios() -> list[dict[str, Any]]:
    with SCENARIOS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)["scenarios"]


def evaluate_expectations(result: dict[str, Any], scenario: dict[str, Any]) -> tuple[bool, list[str]]:
    errs: list[str] = []
    exp = scenario.get("expects", {})

    if "unsafe_policy_create_status" in exp:
        got = result.get("unsafe_policy_create", {}).get("status_code")
        if got != exp["unsafe_policy_create_status"]:
            errs.append(f"unsafe_policy_create status expected {exp['unsafe_policy_create_status']} got {got}")
        return (len(errs) == 0, errs)

    if "self_approve_status" in exp:
        got = result.get("flow", {}).get("self_approve", {}).get("status_code")
        if got != exp["self_approve_status"]:
            errs.append(f"self_approve status expected {exp['self_approve_status']} got {got}")
        return (len(errs) == 0, errs)

    decision = result.get("flow", {}).get("evaluate", {}).get("body", {}).get("decision")
    if "decision" in exp and decision != exp["decision"]:
        errs.append(f"decision expected {exp['decision']} got {decision}")
    if "decision_one_of" in exp and decision not in exp["decision_one_of"]:
        errs.append(f"decision expected one of {exp['decision_one_of']} got {decision}")

    execute_status = result.get("flow", {}).get("execute", {}).get("body", {}).get("status")
    if execute_status is None:
        execute_http = result.get("flow", {}).get("execute", {}).get("status_code")
        events = result.get("flow", {}).get("audit", {}).get("events", [])
        if execute_http == 400 and "execution_blocked" in events:
            execute_status = "blocked"
    if "final_status" in exp and execute_status != exp["final_status"]:
        errs.append(f"final_status expected {exp['final_status']} got {execute_status}")
    if "final_status_one_of" in exp and execute_status not in exp["final_status_one_of"]:
        errs.append(f"final_status expected one of {exp['final_status_one_of']} got {execute_status}")

    required_events = exp.get("must_include_events", [])
    events = result.get("flow", {}).get("audit", {}).get("events", [])
    for req in required_events:
        if req not in events:
            errs.append(f"missing audit event {req}")

    return (len(errs) == 0, errs)


def confidence_tier(scenario_id: str) -> tuple[str, str]:
    high = {"policy_safety_reject", "separation_of_duties", "policy_hard_stop", "manual_approval_gate"}
    medium = {"healthy_restart", "broker_not_found", "telemetry_unavailable", "metadata_unavailable"}
    if scenario_id in high:
        return ("high", "pure API/policy/audit logic under deterministic local controls")
    if scenario_id in medium:
        return ("medium", "depends on local containerized service behavior approximating real clusters")
    return ("low", "requires managed-cluster specific controls")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local simulation scenarios and export result artifacts.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--scenario", default="all", help="Scenario id or 'all'")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any scenario fails expectations")
    args = parser.parse_args()

    runner = ScenarioRunner(args.base_url)
    scenarios = load_scenarios()
    if args.scenario != "all":
        scenarios = [s for s in scenarios if s["id"] == args.scenario]
        if not scenarios:
            raise SystemExit(f"Scenario not found: {args.scenario}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ARTIFACTS_DIR / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    all_results: list[dict[str, Any]] = []
    failures = 0

    for i in range(args.iterations):
        tokens = runner.issue_tokens()
        runner.disable_simulation_policies(tokens.admin)
        for s in scenarios:
            row: dict[str, Any] = {"iteration": i + 1, "scenario": s["id"], "description": s["description"]}
            tier, reason = confidence_tier(s["id"])
            row["confidence"] = {"tier": tier, "reason": reason}

            # Fault application is delegated to fault_injection.py by caller to stay deterministic.
            if s.get("unsafe_policy_expr"):
                unsafe_resp = requests.post(
                    f"{runner.api_v1}/policies",
                    headers={**runner._h(tokens.admin), "Content-Type": "application/json"},
                    json={
                        "name": f"unsafe-{stamp}-{i}",
                        "description": "unsafe policy test",
                        "condition_expr": s["unsafe_policy_expr"],
                        "enforcement": "hard_stop",
                        "enabled": True,
                        "scope_platform": "kafka",
                        "scope_change_type": "restart_component",
                    },
                    timeout=30,
                )
                row["unsafe_policy_create"] = {"status_code": unsafe_resp.status_code, "body": unsafe_resp.json() if unsafe_resp.content else {}}
            else:
                enforce_manual = False
                if s.get("requires_policy"):
                    pol = s.get("policy", {})
                    create = runner.create_policy(tokens.admin, pol, suffix=f"{stamp}-{i}-{s['id']}")
                    row["policy_create"] = {"status_code": create.status_code, "body": create.json() if create.content else {}}
                    enforce_manual = pol.get("enforcement") == "manual_approval"

                row["flow"] = runner.run_change_flow(
                    tokens=tokens,
                    target_id=s.get("target_id", "1"),
                    enforce_manual=enforce_manual,
                    run_separation_test=(s["id"] == "separation_of_duties"),
                )

            row["pilot_report"] = runner.get_report(tokens.viewer)
            ok, errors = evaluate_expectations(row, s)
            row["ok"] = ok
            row["errors"] = errors
            failures += 0 if ok else 1
            all_results.append(row)

            time.sleep(0.25)

    summary = {
        "generated_at": stamp,
        "iterations": args.iterations,
        "scenarios_ran": len(all_results),
        "failures": failures,
        "pass_rate": round(((len(all_results) - failures) / len(all_results)) * 100, 2) if all_results else 0.0,
    }

    (out_dir / "results.json").write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(f"artifact_dir={out_dir}")
    if args.strict and failures > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

