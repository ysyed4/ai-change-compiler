# Local Cluster Simulation Toolkit

This directory provides a repeatable local simulation harness for predicting production behavior.

## Files

- `scenarios.json` - machine-readable scenario matrix and expected contracts.
- `scenario_matrix.md` - human-readable scenario summary.
- `fault_injection.py` - deterministic fault controls for local Docker stack.
- `scenario_runner.py` - role-aware scenario execution and artifact export.
- `confidence_model.md` - confidence tier rubric for production extrapolation.

## Prerequisites

- Running stack via `infra/docker/docker-compose.yml`.
- Backend reachable at `http://localhost:8000`.
- Python with `requests` installed.

## Commands

### Reset local faults

```bash
python change-compiler/simulation/fault_injection.py reset
```

### Apply fault

```bash
python change-compiler/simulation/fault_injection.py apply --fault prometheus_down
python change-compiler/simulation/fault_injection.py apply --fault kafka_down
```

### Run one scenario

```bash
python change-compiler/simulation/scenario_runner.py --scenario policy_safety_reject --iterations 1 --strict
```

### Run full batch

```bash
python change-compiler/simulation/scenario_runner.py --scenario all --iterations 10 --strict
```

Outputs are written to `simulation/artifacts/<timestamp>/`.

## Regression Hook

Use strict mode in CI to fail on contract drift:

```bash
python change-compiler/simulation/scenario_runner.py --scenario policy_safety_reject --iterations 1 --strict
python change-compiler/simulation/scenario_runner.py --scenario separation_of_duties --iterations 1 --strict
```

