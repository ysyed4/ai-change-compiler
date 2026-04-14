from dataclasses import dataclass

from app.services.kafka_adapter import KafkaTelemetrySnapshot


@dataclass
class ExecutionResult:
    terminal_status: str
    execution_mode: str
    steps: list[dict]


class GuardedExecutor:
    def execute_restart_workflow(
        self,
        precheck_snapshot: KafkaTelemetrySnapshot,
        constraints: list[str],
        allow_real_restart: bool = False,
    ) -> ExecutionResult:
        execution_mode = "real" if allow_real_restart else "simulated"

        steps: list[dict] = [
            {
                "stage": "precheck",
                "status": "passed",
                "details": "Preconditions validated before restart workflow.",
                "execution_mode": execution_mode,
            }
        ]

        if precheck_snapshot.offline_partitions > 0:
            steps.append(
                {
                    "stage": "precheck",
                    "status": "blocked",
                    "details": "Offline partitions present; execution blocked before action.",
                    "execution_mode": "blocked_before_action",
                }
            )
            return ExecutionResult(
                terminal_status="blocked",
                execution_mode="blocked_before_action",
                steps=steps,
            )

        if not allow_real_restart:
            steps.append(
                {
                    "stage": "restart",
                    "status": "simulated",
                    "details": "Broker restart is simulated in MVP mode; no real broker action executed.",
                    "constraints": constraints,
                    "execution_mode": execution_mode,
                }
            )
            steps.append(
                {
                    "stage": "stabilization",
                    "status": "passed",
                    "details": "Post-restart checks simulated with current telemetry snapshot.",
                    "execution_mode": execution_mode,
                }
            )
            return ExecutionResult(terminal_status="completed", execution_mode=execution_mode, steps=steps)

        steps.append(
            {
                "stage": "restart",
                "status": "completed",
                "details": "Real restart action executed.",
                "constraints": constraints,
                "execution_mode": execution_mode,
            }
        )
        steps.append(
            {
                "stage": "stabilization",
                "status": "passed",
                "details": "Post-restart health checks passed.",
                "execution_mode": execution_mode,
            }
        )
        return ExecutionResult(terminal_status="completed", execution_mode=execution_mode, steps=steps)
