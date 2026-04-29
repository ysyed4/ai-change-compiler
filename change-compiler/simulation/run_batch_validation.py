#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PATH = ROOT / "simulation" / "scenarios.json"
ARTIFACTS_DIR = ROOT / "simulation" / "artifacts"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)


def main() -> None:
    scenarios = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))["scenarios"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ARTIFACTS_DIR / f"batch-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    runs = []
    for scenario in scenarios:
        scenario_id = scenario["id"]
        fault = scenario.get("fault", "none")

        run(["python", "simulation/fault_injection.py", "reset"])
        if fault != "none":
            run(["python", "simulation/fault_injection.py", "apply", "--fault", fault])
        time.sleep(3)

        proc = run(
            [
                "python",
                "simulation/scenario_runner.py",
                "--scenario",
                scenario_id,
                "--iterations",
                "3",
                "--strict",
            ]
        )
        runs.append(
            {
                "scenario": scenario_id,
                "fault": fault,
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }
        )

    run(["python", "simulation/fault_injection.py", "reset"])

    failed = [r for r in runs if r["returncode"] != 0]
    summary = {
        "generated_at": stamp,
        "total_scenarios": len(runs),
        "failed_scenarios": [r["scenario"] for r in failed],
        "pass_rate": round(((len(runs) - len(failed)) / len(runs)) * 100, 2) if runs else 0.0,
    }

    (out_dir / "batch_runs.json").write_text(json.dumps(runs, indent=2), encoding="utf-8")
    (out_dir / "batch_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"artifact_dir={out_dir}")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

