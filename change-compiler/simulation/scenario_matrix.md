# Scenario Matrix

This matrix defines local simulation scenarios and expected outcomes for the Change Compiler stack.

| Scenario ID | Input Condition | Expected Decision | Expected Status Flow | Expected Audit Events | Pilot Report Delta |
|---|---|---|---|---|---|
| `healthy_restart` | All services up, valid broker target | `allow` or `allow_with_constraints` | `received -> evaluated -> executing -> completed` (or precheck blocked) | `change_submitted`, `change_evaluated`, `execution_finished` | `total_changes +1`, possible `approved_changes +1` |
| `broker_not_found` | Invalid target broker ID | `block` | `received -> blocked` | `change_submitted`, `change_evaluated`, `execution_blocked` | `blocked_risky_changes +1` |
| `telemetry_unavailable` | Prometheus down | `block` | `received -> blocked` | `change_submitted`, `change_evaluated`, `execution_blocked` | `blocked_risky_changes +1` |
| `metadata_unavailable` | Kafka brokers stopped | `block` | `received -> blocked` | `change_submitted`, `change_evaluated`, `execution_blocked` | `blocked_risky_changes +1` |
| `policy_hard_stop` | Active policy with `hard_stop` and always-true expression | `block` | `received -> blocked` | `change_submitted`, `change_evaluated`, `execution_blocked` | `blocked_risky_changes +1` |
| `manual_approval_gate` | Active policy with `manual_approval` and always-true expression | `allow*` then approval gate | `received -> paused/evaluated -> executing/completed` | `change_submitted`, `change_evaluated`, `change_approved`, `execution_finished` | `requires_manual_approval +1`, `approved_changes +1` |
| `separation_of_duties` | Same identity is requester and attempts approval | N/A (approval control) | Approval blocked before execution | `change_submitted`, `change_evaluated`, failed approve call | No successful approval increment |
| `policy_safety_reject` | Unsafe expression policy create attempt | N/A (policy API validation) | N/A | N/A | No policy created |

## Notes
- The local simulation harness reads the machine-readable source from `simulation/scenarios.json`.
- Some scenarios allow multiple terminal statuses because runtime prechecks can block execution safely.
- The key contract is safety and correctness: no unsafe execution when preconditions fail.

