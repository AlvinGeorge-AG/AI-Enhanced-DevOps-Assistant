import urllib.request
import sys
import time

# --- Timing math (matches infra/prometheus/alert_rules.yml: HighCPUUsage) ---
# expr: avg(rate(process_cpu_seconds_total[1m])) * 100 > 80   for: 2m
#
#   - rate(...[1m]) needs ~1 full minute of samples at the new (high) CPU
#     level before the rate calculation fully reflects the spike.
#   - for: 2m means Prometheus only flips the alert to "firing" after it has
#     stayed above threshold for 2 *additional* minutes once it crosses.
#   - scrape_interval is 5s, so there's no scrape-frequency risk here.
#
# Total worst-case time-to-fire ≈ 1m (rate window fill) + 2m (for: duration)
# = 3 minutes. We wait 3.5 minutes (210s) with a 30s safety margin on top,
# and the chaos endpoint itself now sustains the spike for 210s with zero
# sleep gaps (see app.py), so the load comfortably outlasts this wait.

WAIT_SECONDS = 210 + 30  # 4 minutes total: matches/exceeds chaos endpoint duration + margin

print("\n🔥 REAL-WORLD SCENARIO: VIRAL TRAFFIC SURGE 🔥")
print("Triggering a sustained, sleep-free CPU spike (no gaps, no luck involved)...\n")

try:
    resp = urllib.request.urlopen("http://localhost/chaos/cpu", timeout=5)
    print(f"✅ {resp.read().decode().strip()}")
except Exception as e:
    print(f"❌ Failed to reach /chaos/cpu: {e}")
    print("   Is the stack up? (docker compose ps)")
    sys.exit(1)

print(f"\n⏳ Holding for {WAIT_SECONDS}s so Prometheus's rate[1m] window fills")
print("   and the alert's `for: 2m` duration fully elapses before you check logs.")
print("   (This script does NOT tail logs -- check them yourself once this finishes,")
print("    or in another terminal right now with: docker compose logs -f sentinel_api)\n")

try:
    for remaining in range(WAIT_SECONDS, 0, -5):
        mins, secs = divmod(remaining, 60)
        print(f"   ...{mins}m{secs:02d}s remaining", end="\r", flush=True)
        time.sleep(5)
    print(" " * 40, end="\r")
except KeyboardInterrupt:
    print("\n\n🛑 Wait interrupted -- chaos thread is still running server-side regardless.")
    sys.exit(0)

print("✅ Wait complete. The alert should have fired by now (or fired and resolved")
print("   if CPU dropped). Check the dashboard / sentinel_api logs to confirm:")
print("   docker compose logs sentinel_api | tail -n 100\n")
