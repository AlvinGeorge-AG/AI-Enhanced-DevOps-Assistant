import urllib.request
import sys
import time

# --- Timing math (matches infra/prometheus/alert_rules.yml: HighCPUUsage) ---
# expr: avg(rate(process_cpu_seconds_total[15s])) * 100 > 75   for: 15s
#
# rate(...[15s]) fills in ~15s; for: 15s once the threshold is crossed.
# Worst case ≈ 15s (window) + 15s (for:) = 30s for alert to fire.
# Then: webhook → LLM decision → Docker scale_up ≈ 15-30s more.
# Total pipeline: ~45-60s.
#
# The /chaos/cpu endpoint keeps threads hot for 300s (5 minutes), so:
#   - The alert fires while CPU is still pinned high ✅
#   - The LLM decides and executes scale_up while CPU is still high ✅
#   - Grafana clearly shows the effect of scale_up on a still-loaded system ✅
#   - ~240s of stress remains AFTER the action, proving the fix worked ✅
#
# The 120s cooldown prevents a second scale_up, and by that time the
# per-replica CPU has already dropped (load spread across more replicas),
# so the alert resolves naturally. No runaway scaling.

WAIT_SECONDS = 15 + 15 + 20  # rate window + for: duration + safety margin

print("\n🔥 REAL-WORLD SCENARIO: VIRAL TRAFFIC SURGE 🔥")
print("Simulating a massive CPU spike across the application...")
print(f"   CPU will stay pinned HIGH for 5 MINUTES (300s) — long enough for")
print(f"   the full detection → alert → LLM → scale_up pipeline to act.\n")

try:
    urllib.request.urlopen("http://localhost/chaos/cpu", timeout=5)
    print("✅ CPU threads locked at high capacity (GIL-yielding loop, 300s duration).")
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
    print("\n\n🛑 Wait interrupted — CPU threads are still burning in the container (300s total).")
    sys.exit(0)

print("✅ Alert window elapsed. The pipeline should now be in action.")
print("   CPU stress is STILL RUNNING for several more minutes — watch Grafana!\n")
print("📊 WHAT TO WATCH ON GRAFANA:")
print("   1. CPU stays HIGH even after this script finishes (stress runs 300s total)")
print("   2. Alert fires → LLM decides scale_up → new replica comes online")
print("   3. Per-replica CPU DROPS as load spreads across more containers")
print("   4. This proves the system works: stress is still active, but managed\n")
print("   docker compose logs sentinel_api | tail -n 100\n")
