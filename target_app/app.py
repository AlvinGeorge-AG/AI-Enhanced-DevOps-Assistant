from flask import Flask, abort
from prometheus_flask_exporter import PrometheusMetrics
import time
import os
import threading

app = Flask(__name__)
# This automatically exposes /metrics AND tracks all HTTP traffic/errors!
metrics = PrometheusMetrics(app)

# A global list to hold junk data for our memory leak simulation
memory_leak_storage = []

# How long a single /chaos/cpu hit pins the CPU for. Must outlast the
# alert's `for:` duration plus the rate() lookback (see alert_rules.yml).
CPU_SPIKE_DURATION_SECONDS = 90

# Thread count: oversubscribe relative to available cores so every core
# has more than one runnable thread fighting for it at all times. Even
# under the GIL, a tight CPU-bound loop with NO sleep/yield forces near-100%
# reported process_cpu_seconds_total, because the interpreter only releases
# the GIL on its own check-interval, not voluntarily idling.
_cpu_count = os.cpu_count() or 2
CPU_SPIKE_THREADS = max(4, _cpu_count * 2)


def background_cpu_spike(end_time: float):
    """Chunked busy-loop. Burns hot, then yields the GIL so Werkzeug can
    answer Prometheus scrapes on :5000/metrics without timing out."""
    x = 0
    while time.time() < end_time:
        for _ in range(10_000):
            x = (x * 1234567 + 1) % 99999999
        time.sleep(0.002)

@app.route('/')
def hello():
    return "Target App is Running!"

# --- CHAOS ENGINEERING ENDPOINTS ---

@app.route('/chaos/cpu')
def chaos_cpu():
    end_time = time.time() + CPU_SPIKE_DURATION_SECONDS
    for _ in range(CPU_SPIKE_THREADS):
        threading.Thread(target=background_cpu_spike, args=(end_time,), daemon=True).start()
    return (
        f"Chaos injected: CPU spike started across {CPU_SPIKE_THREADS} threads "
        f"for {CPU_SPIKE_DURATION_SECONDS}s (GIL-yielding loop)."
    )

@app.route('/chaos/memory')
def chaos_memory():
    # Appends 50MB of junk string data into RAM every time you hit this URL
    junk_data = "A" * 50_000_000 
    memory_leak_storage.append(junk_data)
    return f"Chaos injected: Leaked 50MB of Memory. Total chunks: {len(memory_leak_storage)}"

@app.route('/chaos/error')
def chaos_error():
    # Intentionally crashes this specific request with an HTTP 500 Internal Server Error
    abort(500, description="Chaos injected: Simulated database connection failure!")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)