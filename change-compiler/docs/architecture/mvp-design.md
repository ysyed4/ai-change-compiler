# Change Compiler MVP Design (Kafka Broker Restart Vertical Slice)

## Scope

This implementation is intentionally narrow:
- One-broker-at-a-time Kafka restart change requests.
- Pre-change evaluation using telemetry + metadata.
- Guarded execution with explicit execution mode.
- Full audit timeline persistence.

## Decision data sources

- **Telemetry (Prometheus):** queried via `/api/v1/query` for offline partitions, URPs, lag, disk pressure, and controller signal.
- **Metadata (Kafka AdminClient):** broker IDs, topics, partitions, and target broker leader assignment.

## Source status model

Each evaluation reports:
- `telemetry_source_status`: `real`, `partial`, `fallback`
- `metadata_source_status`: `real`, `fallback`

Rules treat unavailable data as a safety risk.

## Execution model

- `real`: enabled only when `EXECUTE_REAL_RESTART=true`
- `simulated`: default guarded dry-run mode
- `blocked_before_action`: prechecks failed at execute time

## API surface

- `POST /api/v1/changes`
- `POST /api/v1/changes/{id}/evaluate`
- `POST /api/v1/changes/{id}/execute`
- `GET /api/v1/changes/{id}`
- `GET /api/v1/changes/{id}/audit`
