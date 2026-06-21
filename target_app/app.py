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

# How long a single /chaos/cpu hit pins the CPU for. Kept generous so it
# comfortably outlasts Prometheus's `for: 2m` alert window plus the 1m
# rate() lookback that has to fill with high-CPU samples first.
CPU_SPIKE_DURATION_SECONDS = 210  # 3.5 minutes

# Thread count: oversubscribe relative to available cores so every core
# has more than one runnable thread fighting for it at all times. Even
# under the GIL, a tight CPU-bound loop with NO sleep/yield forces near-100%
# reported process_cpu_seconds_total, because the interpreter only releases
# the GIL on its own check-interval, not voluntarily idling.
_cpu_count = os.cpu_count() or 2
CPU_SPIKE_THREADS = max(4, _cpu_count * 2)


def background_cpu_spike(end_time: float):
    """Chunked busy-loop. Burns hot for ~4ms, then yields the GIL for 1ms 
    so Flask's network thread can successfully answer Prometheus scrapes!"""
    x = 0
    while time.time() < end_time:
        # 50,000 raw integer loops takes roughly 4 milliseconds
        for _ in range(50_000):
            x = (x * 1234567 + 1) % 99999999
            
        # Explicitly open the GIL window for 1ms to serve /metrics
        time.sleep(0.001)

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
        f"for {CPU_SPIKE_DURATION_SECONDS}s (no sleep gaps)."
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