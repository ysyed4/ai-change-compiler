from dataclasses import dataclass

from app.services.kafka_adapter import KafkaMetadataSnapshot, KafkaTelemetrySnapshot


@dataclass
class RuleResult:
    decision: str
    risk_score: int
    explanations: list[str]
    constraints: list[str]
    rule_hits: list[dict]


class RulesEngine:
    def evaluate(
        self,
        telemetry: KafkaTelemetrySnapshot,
        metadata: KafkaMetadataSnapshot,
        telemetry_source_status: str,
        metadata_source_status: str,
        telemetry_errors: list[str],
        metadata_errors: list[str],
    ) -> RuleResult:
        explanations: list[str] = []
        constraints: list[str] = []
        rule_hits: list[dict] = []

        if not metadata.broker_exists:
            explanations.append("Blocked: target broker does not exist in Kafka metadata.")
            if metadata_errors:
                explanations.extend(metadata_errors)
            rule_hits.append({"rule": "block_missing_broker", "matched": True})
            return RuleResult("block", 95, explanations, constraints, rule_hits)

        if telemetry_source_status == "fallback" and metadata_source_status == "fallback":
            explanations.append("Blocked: cluster health cannot be verified safely (telemetry and metadata unavailable).")
            explanations.extend(telemetry_errors)
            explanations.extend(metadata_errors)
            rule_hits.append({"rule": "block_unverifiable_cluster", "matched": True})
            return RuleResult("block", 92, explanations, constraints, rule_hits)

        if telemetry.offline_partitions > 0:
            explanations.append("Blocked: offline partitions are currently present.")
            rule_hits.append({"rule": "block_offline_partitions", "matched": True})
            return RuleResult("block", 90, explanations, constraints, rule_hits)

        if metadata_source_status != "real":
            explanations.append("Blocked: Kafka metadata could not be fully verified.")
            explanations.extend(metadata_errors)
            rule_hits.append({"rule": "block_missing_metadata", "matched": True})
            return RuleResult("block", 85, explanations, constraints, rule_hits)

        risk_score = 20

        if telemetry_source_status != "real":
            risk_score += 25
            explanations.append("Telemetry is partially unavailable; proceeding requires constraints.")
            constraints.append("Require operator confirmation before execute due to incomplete telemetry.")
            rule_hits.append({"rule": "partial_telemetry_guard", "matched": True})

        if telemetry.under_replicated_partitions > 0:
            risk_score += 20
            explanations.append("Under-replicated partitions detected.")
            constraints.append("Wait until under-replicated partitions return to zero.")
            rule_hits.append({"rule": "urp_guard", "matched": True})

        if telemetry.broker_disk_usage_percent >= 80:
            risk_score += 20
            explanations.append("Broker disk usage is elevated.")
            constraints.append("Pause if broker disk usage rises above 85%.")
            rule_hits.append({"rule": "disk_guard", "matched": True})

        if telemetry.consumer_lag >= 100:
            risk_score += 20
            explanations.append("Consumer lag is elevated.")
            constraints.append("Pause if consumer lag increases by more than 20%.")
            rule_hits.append({"rule": "lag_guard", "matched": True})

        if telemetry.controller_change_rate > 1:
            explanations.append("Blocked: controller instability detected.")
            rule_hits.append({"rule": "controller_stability", "matched": True})
            return RuleResult("block", max(risk_score, 85), explanations, constraints, rule_hits)

        decision = "allow" if risk_score < 40 else "allow_with_constraints"

        if metadata.leader_partitions_on_target > 0:
            constraints.append("Restart only this single broker and wait for replication recovery before any next action.")
            explanations.append(
                f"Target broker currently leads {metadata.leader_partitions_on_target} partitions; one-broker-at-a-time enforced."
            )
            if decision == "allow":
                decision = "allow_with_constraints"

        if not explanations:
            explanations.append("Cluster health appears stable for a one-broker restart workflow.")

        return RuleResult(
            decision=decision,
            risk_score=min(risk_score, 100),
            explanations=explanations,
            constraints=constraints,
            rule_hits=rule_hits,
        )
