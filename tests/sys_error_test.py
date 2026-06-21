import urllib.request
import urllib.error
import sys
import time
import threading

# --- Timing math (matches infra/prometheus/alert_rules.yml: HighErrorRate) ---
# expr: sum(rate(..._count{status=~"5.."}[1m])) / sum(rate(..._count[1m])) * 100 > 5
#   for: 1m
#
#   - rate(...[1m]) needs ~1 minute of all-5xx traffic to fully fill the
#     window (older, pre-chaos requests still inside the window dilute the
#     ratio downward until they age out).
#   - for: 1m additional duration once the ratio crosses 5%.
#   - scrape_interval 5s is fine, no risk there.
#
# Worst case ≈ 1m (window fill) + 1m (for: duration) = 2 minutes.
# We fire continuously for 3 minutes (180s) total -- comfortable margin --
# at a request rate fast enough to dominate the rate() window (every 0.2s,
# i.e. 5 req/s) instead of the original 0.5s/req which was needlessly slow
# for no safety benefit.

FIRE_DURATION_SECONDS = 180  # 3 minutes of sustained 100% error traffic
REQUEST_INTERVAL_SECONDS = 0.2  # 5 req/s -- fast enough to dominate the rate window


def fire_errors(stop_at: float, counter: dict):
    while time.time() < stop_at:
        try:
            urllib.request.urlopen("http://127.0.0.1/chaos/error", timeout=1)
        except urllib.error.HTTPError:
            # Expected -- /chaos/error always returns 500. This IS the signal.
            counter["count"] += 1
        except Exception:
            pass
        time.sleep(REQUEST_INTERVAL_SECONDS)


print("\n🔥 REAL-WORLD SCENARIO: CASCADING 500 ERRORS 🔥")
print(f"Firing continuous 500s at {1/REQUEST_INTERVAL_SECONDS:.0f} req/s for {FIRE_DURATION_SECONDS}s...\n")

counter = {"count": 0}
stop_at = time.time() + FIRE_DURATION_SECONDS
chaos_thread = threading.Thread(target=fire_errors, args=(stop_at, counter), daemon=True)
chaos_thread.start()

print("✅ Chaos thread active -- this is the ONLY traffic hitting the app right now,")
print("   so the error ratio should sit at 100% for the full duration.")
print("   (Not tailing logs -- check separately with: docker compose logs -f sentinel_api)\n")

try:
    while time.time() < stop_at:
        remaining = int(stop_at - time.time())
        mins, secs = divmod(max(remaining, 0), 60)
        print(f"   ...{mins}m{secs:02d}s remaining | {counter['count']} errors fired so far", end="\r", flush=True)
        time.sleep(2)
    print(" " * 60, end="\r")
except KeyboardInterrupt:
    print("\n\n🛑 Wait interrupted -- background thread is daemonized and will die with this process.")
    sys.exit(0)

chaos_thread.join(timeout=5)
print(f"✅ Done. Fired {counter['count']} total 500 errors over {FIRE_DURATION_SECONDS}s.")
print("   Check sentinel_api logs to confirm the alert fired and a decision was made:")
print("   docker compose logs sentinel_api | tail -n 100\n")
