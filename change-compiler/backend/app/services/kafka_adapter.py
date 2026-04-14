from dataclasses import dataclass

from confluent_kafka import KafkaException
from confluent_kafka.admin import AdminClient

from app.services.prometheus_client import PrometheusClient


@dataclass
class KafkaTelemetrySnapshot:
    offline_partitions: int
    under_replicated_partitions: int
    consumer_lag: float
    broker_disk_usage_percent: float
    controller_change_rate: float


@dataclass
class KafkaMetadataSnapshot:
    broker_ids: list[int]
    broker_exists: bool
    topic_count: int
    partition_count: int
    leader_partitions_on_target: int


@dataclass
class AdapterCollectionResult:
    telemetry: KafkaTelemetrySnapshot
    telemetry_source_status: str
    telemetry_errors: list[str]
    metadata: KafkaMetadataSnapshot
    metadata_source_status: str
    metadata_errors: list[str]


class KafkaAdapter:
    def __init__(
        self,
        prometheus_client: PrometheusClient,
        bootstrap_servers: str,
        metadata_timeout_seconds: float = 5.0,
    ):
        self.prometheus_client = prometheus_client
        self.bootstrap_servers = bootstrap_servers
        self.metadata_timeout_seconds = metadata_timeout_seconds

    @staticmethod
    def parse_broker_id(target_id: str) -> int | None:
        candidate = target_id.strip().lower().replace("broker-", "")
        if candidate.isdigit():
            return int(candidate)
        return None

    def _collect_telemetry(self) -> tuple[KafkaTelemetrySnapshot, str, list[str]]:
        query_map = {
            "offline_partitions": "sum(kafka_controller_kafkacontroller_offlinepartitionscount)",
            "under_replicated_partitions": "sum(kafka_server_replicamanager_underreplicatedpartitions)",
            "consumer_lag": "sum(kafka_consumergroup_lag)",
            "broker_disk_usage_percent": "max((node_filesystem_size_bytes{mountpoint=\"/\"} - node_filesystem_avail_bytes{mountpoint=\"/\"}) / node_filesystem_size_bytes{mountpoint=\"/\"} * 100)",
            "controller_change_rate": "sum(rate(kafka_controller_kafkacontroller_activecontrollercount[5m]))",
        }

        fallback = {
            "offline_partitions": 0.0,
            "under_replicated_partitions": 0.0,
            "consumer_lag": 10.0,
            "broker_disk_usage_percent": 65.0,
            "controller_change_rate": 0.0,
        }

        values: dict[str, float] = {}
        errors: list[str] = []
        statuses: set[str] = set()

        for key, query in query_map.items():
            result = self.prometheus_client.query_instant(query)
            statuses.add(result.source_status)
            if result.value is None:
                values[key] = fallback[key]
                if result.error:
                    errors.append(f"{key}: {result.error}")
            else:
                values[key] = result.value

        if statuses == {"real"}:
            source_status = "real"
        elif "real" in statuses:
            source_status = "partial"
        else:
            source_status = "fallback"

        snapshot = KafkaTelemetrySnapshot(
            offline_partitions=int(values["offline_partitions"]),
            under_replicated_partitions=int(values["under_replicated_partitions"]),
            consumer_lag=float(values["consumer_lag"]),
            broker_disk_usage_percent=float(values["broker_disk_usage_percent"]),
            controller_change_rate=float(values["controller_change_rate"]),
        )
        return snapshot, source_status, errors

    def _collect_metadata(self, target_broker_id: int | None) -> tuple[KafkaMetadataSnapshot, str, list[str]]:
        if target_broker_id is None:
            return (
                KafkaMetadataSnapshot(
                    broker_ids=[],
                    broker_exists=False,
                    topic_count=0,
                    partition_count=0,
                    leader_partitions_on_target=0,
                ),
                "fallback",
                ["Target broker id format invalid."],
            )

        try:
            admin = AdminClient({"bootstrap.servers": self.bootstrap_servers})
            metadata = admin.list_topics(timeout=self.metadata_timeout_seconds)
            broker_ids = sorted(int(bid) for bid in metadata.brokers.keys())
            broker_exists = target_broker_id in broker_ids
            topic_count = len(metadata.topics)

            partition_count = 0
            leader_partitions_on_target = 0
            for topic_meta in metadata.topics.values():
                if topic_meta.error is not None:
                    continue
                for partition_meta in topic_meta.partitions.values():
                    partition_count += 1
                    if partition_meta.leader == target_broker_id:
                        leader_partitions_on_target += 1

            return (
                KafkaMetadataSnapshot(
                    broker_ids=broker_ids,
                    broker_exists=broker_exists,
                    topic_count=topic_count,
                    partition_count=partition_count,
                    leader_partitions_on_target=leader_partitions_on_target,
                ),
                "real",
                [],
            )
        except KafkaException as exc:
            return (
                KafkaMetadataSnapshot([], False, 0, 0, 0),
                "fallback",
                [f"Kafka metadata unavailable: {exc}"],
            )
        except Exception as exc:
            return (
                KafkaMetadataSnapshot([], False, 0, 0, 0),
                "fallback",
                [f"Kafka metadata lookup failed: {exc}"],
            )

    def collect_cluster_state(self, target_id: str) -> AdapterCollectionResult:
        target_broker_id = self.parse_broker_id(target_id)

        telemetry, telemetry_status, telemetry_errors = self._collect_telemetry()
        metadata, metadata_status, metadata_errors = self._collect_metadata(target_broker_id)

        return AdapterCollectionResult(
            telemetry=telemetry,
            telemetry_source_status=telemetry_status,
            telemetry_errors=telemetry_errors,
            metadata=metadata,
            metadata_source_status=metadata_status,
            metadata_errors=metadata_errors,
        )
