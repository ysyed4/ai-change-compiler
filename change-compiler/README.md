# Change Compiler

Change Compiler is a cross-platform change safety controller. This MVP is tightly scoped to Kafka broker restart evaluation and guarded execution.

## What is real in this MVP

- Real FastAPI workflow for submit, evaluate, execute, and audit retrieval.
- Real PostgreSQL persistence via SQLAlchemy and Alembic migrations.
- Real Prometheus query attempts for Kafka health signals.
- Real Kafka metadata lookup via Kafka AdminClient to verify broker existence and cluster metadata.
- Rules engine decisions based on telemetry and metadata source availability.

## What is simulated/fallback

- Broker restart execution defaults to **simulated** mode (`EXECUTE_REAL_RESTART=false`).
- Telemetry falls back to safe default values when Prometheus cannot provide data.
- Metadata/telemetry failures lead to constrained or blocked decisions; no silent success.

## Run locally

```bash
cd "/Users/yousefali/Desktop/AIKafka/change-compiler/infra/docker"
docker compose up --build
```

### Verify stack

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:9090/-/healthy
```

## API quick demo

### 1) Create change

```bash
curl -X POST http://localhost:8000/api/v1/changes \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "kafka",
    "change_type": "restart_component",
    "target": {"type": "broker", "id": "broker-1"},
    "reason": "maintenance restart"
  }'
```

### 2) Evaluate change

```bash
curl -X POST http://localhost:8000/api/v1/changes/<change_id>/evaluate
```

### 3) Execute change (guarded)

```bash
curl -X POST http://localhost:8000/api/v1/changes/<change_id>/execute
```

### 4) Read audit timeline

```bash
curl http://localhost:8000/api/v1/changes/<change_id>/audit
```
