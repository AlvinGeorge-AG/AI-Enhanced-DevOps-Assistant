import urllib.request
import sys
import time

CHAOS_HITS = 5  # +250MB on top of baseline -- comfortable margin over 150MB
WAIT_SECONDS = 60 + 30  # the for:1m duration + safety margin

print("\n🔥 REAL-WORLD SCENARIO: GENUINE HIGH-LOAD TRAFFIC SURGE 🔥")
print("Simulating a massive CPU spike combined with high memory usage...\n")

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
print("\nFiring /chaos/cpu to spike CPU...")
try:
    urllib.request.urlopen("http://localhost/chaos/cpu", timeout=5)
    print("✅ CPU threads locked at high capacity (GIL-yielding loop, 90s duration).")
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

print("✅ Wait complete. Check sentinel_api logs to confirm the alert fired:")
print("   docker compose logs sentinel_api | tail -n 100")
print("\n⚠️  Note: With BOTH CPU and memory elevated, the AI should decide to scale_up,")
print("   not restart, because the high memory is seen as part of high traffic load.\n")
