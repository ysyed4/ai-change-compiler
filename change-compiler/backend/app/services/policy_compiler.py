from dataclasses import dataclass

from app.models.policy import Policy


@dataclass
class PolicyCompilationResult:
    decision_override: str | None
    constraints: list[str]
    explanations: list[str]
    policy_hits: list[dict]


class PolicyCompiler:
    def evaluate(self, policies: list[Policy], context: dict) -> PolicyCompilationResult:
        decision_override: str | None = None
        constraints: list[str] = []
        explanations: list[str] = []
        policy_hits: list[dict] = []

        safe_globals: dict[str, object] = {"__builtins__": {}}
        for policy in policies:
            if not policy.enabled:
                continue

            matched = False
            try:
                matched = bool(eval(policy.condition_expr, safe_globals, context))
            except Exception:
                matched = False

            policy_hits.append(
                {
                    "policy": policy.name,
                    "matched": matched,
                    "enforcement": policy.enforcement.value,
                }
            )

            if not matched:
                continue

            if policy.enforcement.value == "hard_stop":
                decision_override = "block"
                explanations.append(f"Policy hard stop triggered: {policy.name}.")
            elif policy.enforcement.value == "manual_approval":
                constraints.append(f"Manual approval required by policy: {policy.name}.")
                explanations.append(f"Policy approval gate triggered: {policy.name}.")

        return PolicyCompilationResult(
            decision_override=decision_override,
            constraints=constraints,
            explanations=explanations,
            policy_hits=policy_hits,
        )
