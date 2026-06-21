import httpx
import math
from executor.memory import get_recent_logs

PROMETHEUS_URL = "http://prometheus:9090/api/v1/query"

class ContextBuilder:
    async def get_system_state(self) -> dict:
        queries = {
            "cpu_usage_percent": 'avg(rate(process_cpu_seconds_total{job="target_app"}[1m])) * 100',
            "memory_usage_mb": 'sum(process_resident_memory_bytes{job="target_app"}) / 1024 / 1024',
            "error_rate_percent": 'sum(rate(flask_http_request_duration_seconds_count{job="target_app", status=~"5.."}[1m])) / sum(rate(flask_http_request_duration_seconds_count{job="target_app"}[1m])) * 100',
            "request_rate_per_sec": 'sum(rate(flask_http_request_duration_seconds_count{job="target_app"}[1m]))',
            "active_replicas": 'count(up{job="target_app"} == 1)',
            
            # Remove '== 1' so we count registered targets, preventing Coma false-positives
            "active_replicas": 'count(up{job="target_app"})',
        }

        state = {}
        async with httpx.AsyncClient() as client:
            for key, query in queries.items():
                try:
                    response = await client.get(PROMETHEUS_URL, params={"query": query})
                    data = response.json()
                    results = data.get('data', {}).get('result', [])
                    if results:
                        raw_val = float(results[0]['value'][1])
                        if math.isnan(raw_val):
                            raw_val = 0.0
                        state[key] = round(raw_val, 2)
                    else:
                        state[key] = 0.0
                except Exception:
                    state[key] = 0.0

        state["recent_history"] = get_recent_logs(limit=3)
        return state