import urllib.request
import sys
import time

# --- Timing math (matches infra/prometheus/alert_rules.yml: HighMemoryUsage) ---
# expr: sum(process_resident_memory_bytes) / 1024 / 1024 > 150   for: 1m
#
# Unlike the CPU/error alerts this is a plain instant gauge threshold, not
# a rate() -- no 1m window needs to "fill" first. Once cluster-wide RSS
# crosses 150MB and STAYS above it for 60s straight, it fires. No ramp-up
# risk here, just need to clear the threshold by a comfortable margin so a
# GC pass or measurement jitter doesn't dip it back under 150 mid-window.
#
# Baseline per replica sits around ~30-35MB (per sentinel_api's own logs).
# /chaos/memory adds 50MB of retained string data PER HIT, permanently
# (it's appended to a list, never freed). 4 hits = +200MB, which combined
# with baseline comfortably clears 150MB with margin to spare -- one or
# two hits would be cutting it close depending on which replica gets hit
# by Docker's round-robin/least-conn balancing.

CHAOS_HITS = 5  # +250MB on top of baseline -- comfortable margin over 150MB
WAIT_SECONDS = 60 + 30  # the for:1m duration + safety margin

print("\n🔥 REAL-WORLD SCENARIO: MEMORY LEAK / RUNAWAY PROCESS 🔥")
print(f"Firing {CHAOS_HITS}x /chaos/memory (50MB retained each, never freed)...\n")

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
    time.sleep(0.5)  # tiny stagger so requests don't all land on the exact same replica tick

print(f"\n✅ Leaked ~{total_leaked_mb}MB across the fleet. This is permanent until containers restart.")
print(f"\n⏳ Holding for {WAIT_SECONDS}s so the alert's `for: 1m` duration fully elapses.")
print("   (Not tailing logs -- check separately with: docker compose logs -f sentinel_api)\n")

try:
    for remaining in range(WAIT_SECONDS, 0, -5):
        mins, secs = divmod(remaining, 60)
        print(f"   ...{mins}m{secs:02d}s remaining", end="\r", flush=True)
        time.sleep(5)
    print(" " * 40, end="\r")
except KeyboardInterrupt:
    print("\n\n🛑 Wait interrupted -- the leaked memory is still sitting in the container regardless.")
    sys.exit(0)

print("✅ Wait complete. Check sentinel_api logs to confirm the alert fired:")
print("   docker compose logs sentinel_api | tail -n 100")
print("\n⚠️  Note: scale_up will NOT fix a memory leak (new replicas just get more memory")
print("   to leak into). Watch what the AI actually decides here -- restart_container")
print("   is the structurally correct call, not scale_up. Good test of whether the LLM")
print("   reasons about this correctly vs. just pattern-matching 'high metric -> scale up'.\n")
