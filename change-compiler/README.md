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
cd change-compiler/infra/docker
docker compose up --build
```

Prerequisites:

- Docker Desktop (or Docker Engine) is running.
- `.env` exists at `change-compiler/.env` (you can copy from `.env.example`).

### Verify stack

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:9090/-/healthy
```

## API quick demo (with auth)

### 0) Get a dev token

```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@company.com","roles":["requester","approver","executor","viewer","admin"],"org_id":"default-org"}'
```

Use the returned `access_token` as `TOKEN` below.

### 1) Create change

```bash
curl -X POST http://localhost:8000/api/v1/changes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "kafka",
    "change_type": "restart_component",
    "target": {"type": "broker", "id": "broker-1"},
    "reason": "maintenance restart",
    "org_id": "default-org"
  }'
```

### 2) Evaluate change

```bash
curl -X POST http://localhost:8000/api/v1/changes/<change_id>/evaluate \
  -H "Authorization: Bearer $TOKEN"
```

### 3) Approve change (if manual approval required)

```bash
curl -X POST http://localhost:8000/api/v1/changes/<change_id>/approve \
  -H "Authorization: Bearer $TOKEN"
```

### 4) Execute change (guarded)

```bash
curl -X POST http://localhost:8000/api/v1/changes/<change_id>/execute \
  -H "Authorization: Bearer $TOKEN"
```

### 5) Read audit timeline

```bash
curl http://localhost:8000/api/v1/changes/<change_id>/audit \
  -H "Authorization: Bearer $TOKEN"
```

### 6) Pilot value report

```bash
curl http://localhost:8000/api/v1/reports/pilot-value \
  -H "Authorization: Bearer $TOKEN"
```

## Production reference deployment

Kubernetes Helm deployment assets are not included in this repository snapshot. Add your
deployment manifests/chart in a dedicated `deploy/` directory before using a production
install flow.
