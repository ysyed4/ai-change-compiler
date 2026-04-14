from dataclasses import dataclass

import requests


@dataclass
class MetricFetchResult:
    value: float | None
    source_status: str
    error: str | None = None


class PrometheusClient:
    def __init__(self, base_url: str, timeout_seconds: float = 3.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def query_instant(self, query: str) -> MetricFetchResult:
        endpoint = f"{self.base_url}/api/v1/query"
        try:
            response = requests.get(endpoint, params={"query": query}, timeout=self.timeout_seconds)
            response.raise_for_status()
            data = response.json()
            result = data.get("data", {}).get("result", [])
            if not result:
                return MetricFetchResult(value=None, source_status="partial", error=f"No data for {query}")

            raw_value = result[0].get("value", [None, None])[1]
            if raw_value is None:
                return MetricFetchResult(value=None, source_status="partial", error=f"Malformed data for {query}")
            return MetricFetchResult(value=float(raw_value), source_status="real")
        except Exception as exc:
            return MetricFetchResult(value=None, source_status="fallback", error=str(exc))
