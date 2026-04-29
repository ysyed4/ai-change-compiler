# Confidence Model

This model classifies how strongly local simulation results predict real-cluster behavior.

## Tier Definitions

- **High**
  - Scope: auth, RBAC, policy parser safety, approval gate, audit event sequencing.
  - Why: deterministic application-layer logic independent of managed Kafka/cloud specifics.
  - Promotion criteria: 100% pass across repeated runs for these controls.

- **Medium**
  - Scope: Kafka/Prometheus availability scenarios, metadata fallback behavior, restart prechecks.
  - Why: local Docker behavior approximates but does not fully replicate managed-cluster networking and control planes.
  - Promotion criteria: >=90% pass with stable outcomes over batch runs.

- **Low**
  - Scope: IAM/TLS integration, cloud service quotas, cross-region latency, provider-specific Kafka behavior.
  - Why: requires real managed infrastructure and security integrations not represented locally.
  - Promotion criteria: validated in pilot or staging environment with provider-native controls.

## Reason Codes

- `app_deterministic`: Result depends only on backend code path and request payload.
- `container_approximation`: Result depends on local container runtime approximating production.
- `provider_specific`: Result requires cloud/provider integration to validate.

## Decision Rule

- **Local predictive Go**:
  - High-tier scenarios all pass.
  - Medium-tier scenarios pass rate >= 90%.
  - No regression in separation-of-duties or unsafe policy rejection.
- **No-Go**:
  - Any high-tier scenario fails.
  - Medium-tier pass rate < 90%.
  - Audit sequence contract breaks for core change workflow.

