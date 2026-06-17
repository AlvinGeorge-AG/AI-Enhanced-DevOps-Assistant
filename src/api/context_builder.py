# Functions to fetch Prometheus data via HTTP GET
import httpx

# We use "prometheus:9090" because Docker automatically resolves the container name to its internal IP!
PROMETHEUS_URL = "http://prometheus:9090/api/v1/query"

class ContextBuilder:
    async def get_system_state(self) -> dict:
        """Fetches the 'State of the World' directly from the Prometheus API."""
        
        # The exact PromQL queries we want to ask Prometheus
        queries = {
            "cpu_usage_percent": 'rate(process_cpu_seconds_total[1m]) * 100',
            "memory_usage_mb": 'process_resident_memory_bytes / 1024 / 1024',
            "error_rate_percent": 'sum(rate(flask_http_request_duration_seconds_count{status=~"5.."}[1m])) / sum(rate(flask_http_request_duration_seconds_count[1m])) * 100',
            "active_replicas": 'count(up{job="target_app"})'
        }

        state = {}
        
        # Open an async HTTP client to talk to Prometheus
        async with httpx.AsyncClient() as client:
            for key, query in queries.items():
                try:
                    response = await client.get(PROMETHEUS_URL, params={"query": query})
                    data = response.json()
                    
                    # Prometheus returns data in a deeply nested JSON structure. We extract the actual number here.
                    results = data.get('data', {}).get('result', [])
                    if results:
                        # Grab the value and round it to 2 decimal places for the AI
                        value = round(float(results[0]['value'][1]), 2)
                        state[key] = value
                    else:
                        state[key] = 0.0
                except Exception as e:
                    print(f"Error fetching {key}: {e}")
                    state[key] = "error"
        
        return state