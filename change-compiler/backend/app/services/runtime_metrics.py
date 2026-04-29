from collections import Counter
from dataclasses import dataclass, field


@dataclass
class RuntimeMetrics:
    evaluations_by_decision: Counter = field(default_factory=Counter)
    executions_by_status: Counter = field(default_factory=Counter)
    executions_by_mode: Counter = field(default_factory=Counter)
    risk_score_sum: int = 0
    risk_score_count: int = 0

    def record_evaluation(self, *, decision: str, risk_score: int) -> None:
        self.evaluations_by_decision[decision] += 1
        self.risk_score_sum += int(risk_score)
        self.risk_score_count += 1

    def record_execution(self, *, status: str, execution_mode: str) -> None:
        self.executions_by_status[status] += 1
        self.executions_by_mode[execution_mode] += 1

    def snapshot(self) -> dict:
        avg_risk = (self.risk_score_sum / self.risk_score_count) if self.risk_score_count else 0.0
        return {
            "evaluations_by_decision": dict(self.evaluations_by_decision),
            "executions_by_status": dict(self.executions_by_status),
            "executions_by_mode": dict(self.executions_by_mode),
            "average_risk_score": round(avg_risk, 2),
        }


metrics = RuntimeMetrics()

