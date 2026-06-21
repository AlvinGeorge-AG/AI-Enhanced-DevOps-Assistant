import urllib.request
import sys
import time

# --- Timing math (matches infra/prometheus/alert_rules.yml: HighCPUUsage) ---
# expr: avg(rate(process_cpu_seconds_total[15s])) * 100 > 75   for: 15s
#
# rate(...[15s]) fills in ~15s; for: 15s once the threshold is crossed.
# Worst case ≈ 15s (window) + 15s (for:) = 30s. The /chaos/cpu endpoint
# keeps threads hot for 90s, so we only need to wait out the alert window.

WAIT_SECONDS = 15 + 15 + 20  # rate window + for: duration + safety margin

print("\n🔥 REAL-WORLD SCENARIO: VIRAL TRAFFIC SURGE 🔥")
print("Simulating a massive CPU spike across the application...\n")

try:
    urllib.request.urlopen("http://localhost/chaos/cpu", timeout=5)
    print("✅ CPU threads locked at high capacity (GIL-yielding loop, 90s duration).")
except Exception as e:
    print(f"❌ Failed to reach /chaos/cpu: {e}")
    sys.exit(1)

print(f"\n⏳ Holding for {WAIT_SECONDS}s so Prometheus rate() + alert `for:` fully elapse.")
print("   (Not tailing logs — check separately with: docker compose logs -f sentinel_api)\n")

try:
    for remaining in range(WAIT_SECONDS, 0, -5):
        mins, secs = divmod(remaining, 60)
        print(f"   ...{mins}m{secs:02d}s remaining", end="\r", flush=True)
        time.sleep(5)
    print(" " * 40, end="\r")
except KeyboardInterrupt:
    print("\n\n🛑 Wait interrupted — CPU threads may still be running in the container.")
    sys.exit(0)

print("✅ Wait complete. Check sentinel_api logs to confirm the alert fired:")
print("   docker compose logs sentinel_api | tail -n 100\n")
