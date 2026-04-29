#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_DIR = ROOT / "infra" / "docker"


def run_compose(args: list[str]) -> None:
    cmd = ["docker", "compose", *args]
    subprocess.run(cmd, cwd=COMPOSE_DIR, check=True)


def apply_fault(name: str) -> None:
    if name == "none":
        reset_faults()
        return
    if name == "prometheus_down":
        run_compose(["stop", "prometheus"])
        return
    if name == "kafka_down":
        run_compose(["stop", "kafka1", "kafka2", "kafka3"])
        return
    raise ValueError(f"Unknown fault: {name}")


def reset_faults() -> None:
    run_compose(["up", "-d", "postgres", "prometheus", "kafka1", "kafka2", "kafka3", "backend", "frontend"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic local fault injection for simulation scenarios.")
    parser.add_argument("action", choices=["apply", "reset"])
    parser.add_argument("--fault", default="none", choices=["none", "prometheus_down", "kafka_down"])
    args = parser.parse_args()

    if args.action == "reset":
        reset_faults()
        return
    apply_fault(args.fault)


if __name__ == "__main__":
    main()

