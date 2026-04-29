#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "simulation" / "artifacts"
REPORT_PATH = ROOT / "simulation" / "prediction_report.md"


def latest_batch_dir() -> Path:
    candidates = sorted([p for p in ARTIFACTS.glob("batch-*") if p.is_dir()])
    if not candidates:
        raise FileNotFoundError("No batch artifacts found.")
    return candidates[-1]


def parse_pass_rate(stdout: str) -> float:
    marker = '"pass_rate":'
    if marker not in stdout:
        return 0.0
    line = [ln for ln in stdout.splitlines() if marker in ln]
    if not line:
        return 0.0
    raw = line[0].split(marker, 1)[1].strip().rstrip(",")
    try:
        return float(raw)
    except ValueError:
        return 0.0


def main() -> None:
    batch_dir = latest_batch_dir()
    runs = json.loads((batch_dir / "batch_runs.json").read_text(encoding="utf-8"))
    summary = json.loads((batch_dir / "batch_summary.json").read_text(encoding="utf-8"))

    rows = []
    for run in runs:
        rows.append(
            {
                "scenario": run["scenario"],
                "fault": run["fault"],
                "pass_rate": parse_pass_rate(run.get("stdout", "")),
                "status": "pass" if run["returncode"] == 0 else "fail",
            }
        )

    high = {"policy_safety_reject", "separation_of_duties", "policy_hard_stop", "manual_approval_gate"}
    medium = {"healthy_restart", "broker_not_found", "telemetry_unavailable", "metadata_unavailable"}

    def tier(scenario: str) -> str:
        if scenario in high:
            return "high"
        if scenario in medium:
            return "medium"
        return "low"

    high_failed = [r["scenario"] for r in rows if tier(r["scenario"]) == "high" and r["status"] == "fail"]
    medium_rows = [r for r in rows if tier(r["scenario"]) == "medium"]
    medium_pass = [r for r in medium_rows if r["status"] == "pass"]
    medium_rate = (len(medium_pass) / len(medium_rows) * 100) if medium_rows else 0.0

    if high_failed or medium_rate < 90.0:
        decision = "NO-GO"
    else:
        decision = "GO"

    lines = []
    lines.append("# Prediction Report")
    lines.append("")
    lines.append(f"- Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Batch artifact: `{batch_dir}`")
    lines.append(f"- Overall pass rate: **{summary.get('pass_rate', 0.0)}%**")
    lines.append(f"- Decision: **{decision}**")
    lines.append("")
    lines.append("## Scenario Outcomes")
    lines.append("")
    lines.append("| Scenario | Tier | Fault | Pass Rate | Status |")
    lines.append("|---|---|---|---:|---|")
    for row in rows:
        lines.append(
            f"| `{row['scenario']}` | {tier(row['scenario'])} | `{row['fault']}` | {row['pass_rate']}% | {row['status']} |"
        )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    if decision == "NO-GO":
        if high_failed:
            lines.append("- High-tier regressions detected.")
            lines.append(f"- High-tier failed scenarios: {', '.join(f'`{x}`' for x in high_failed)}")
        else:
            lines.append("- High-tier scenarios are stable.")
        lines.append("- Medium-tier instability detected.")
        lines.append(f"- Medium-tier aggregate pass rate: {round(medium_rate, 2)}% (target >= 90%).")
    else:
        lines.append("- High-tier controls stable and medium-tier reliability target met.")
    lines.append("")
    lines.append("## Known Real-Cluster Validation Gaps")
    lines.append("")
    lines.append("- IAM/TLS and identity-provider integrations.")
    lines.append("- Managed Kafka provider edge behavior and quota limits.")
    lines.append("- Production network latency/partition patterns across zones/regions.")
    lines.append("")
    lines.append("## Recommended Next Actions")
    lines.append("")
    if high_failed:
        lines.append("- Fix failing high-tier scenarios before pilot go/no-go.")
    else:
        lines.append("- Maintain high-tier controls with CI regression checks.")
    lines.append("- Stabilize medium-tier availability scenarios to >=90% pass rate.")
    lines.append("- Run one managed-cluster smoke test to validate low-confidence assumptions.")
    lines.append("")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote={REPORT_PATH}")


if __name__ == "__main__":
    main()

