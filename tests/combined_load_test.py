import urllib.request
import sys
import time

CHAOS_HITS = 5  # +250MB on top of baseline -- comfortable margin over 150MB
WAIT_SECONDS = 60 + 30  # the for:1m duration + safety margin

print("\n🔥 REAL-WORLD SCENARIO: GENUINE HIGH-LOAD TRAFFIC SURGE 🔥")
print("Simulating a massive CPU spike combined with high memory usage...")
print("   CPU stays pinned for 5 MINUTES (300s) — long enough for the full")
print("   detection → alert → LLM → action pipeline to act visibly.\n")

# 1. Leak memory to trigger HighMemoryUsage (> 150MB)
print(f"Firing {CHAOS_HITS}x /chaos/memory (50MB retained each, never freed) to raise RAM...")
total_leaked_mb = 0
for i in range(1, CHAOS_HITS + 1):
    try:
        resp = urllib.request.urlopen("http://localhost/chaos/memory", timeout=5)
        body = resp.read().decode().strip()
        print(f"  [{i}/{CHAOS_HITS}] {body}")
        total_leaked_mb += 50
    except Exception as e:
        print(f"  [{i}/{CHAOS_HITS}] ❌ Failed to reach /chaos/memory: {e}")
        sys.exit(1)
    time.sleep(0.5)

# 2. Trigger CPU spike to trigger HighCPUUsage (> 75%)
print("\nFiring /chaos/cpu to spike CPU (300s duration)...")
try:
    urllib.request.urlopen("http://localhost/chaos/cpu", timeout=5)
    print("✅ CPU threads locked at high capacity (GIL-yielding loop, 300s duration).")
except Exception as e:
    print(f"❌ Failed to reach /chaos/cpu: {e}")
    sys.exit(1)

print(f"\n⏳ Holding for {WAIT_SECONDS}s so both CPU and Memory alerts can fire together.")
print("   (Not tailing logs -- check separately with: docker compose logs -f sentinel_api)\n")

try:
    for remaining in range(WAIT_SECONDS, 0, -5):
        mins, secs = divmod(remaining, 60)
        print(f"   ...{mins}m{secs:02d}s remaining", end="\r", flush=True)
        time.sleep(5)
    print(" " * 40, end="\r")
except KeyboardInterrupt:
    print("\n\n🛑 Wait interrupted -- test stopped.")
    sys.exit(0)

print("✅ Alert window elapsed. The pipeline should now be in action.")
print("   CPU stress is STILL RUNNING for several more minutes — watch Grafana!\n")
print("📊 WHAT TO WATCH ON GRAFANA:")
print("   1. Memory stays HIGH permanently (leaked, never freed) until restart")
print("   2. CPU stays HIGH for 300s total — still burning after this script")
print("   3. Both alerts fire → LLM sees combined load → decides scale_up")
print("   4. Per-replica CPU DROPS as load spreads, proving the action worked\n")
print("⚠️  Note: With BOTH CPU and memory elevated, the AI should decide to scale_up,")
print("   not restart, because the high memory is seen as part of high traffic load.\n")
print("   docker compose logs sentinel_api | tail -n 100\n")
