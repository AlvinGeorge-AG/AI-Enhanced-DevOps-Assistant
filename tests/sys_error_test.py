import urllib.request
import urllib.error
import subprocess
import sys
import time
import threading

def fire_errors():
    """Runs continuously in the background for 4 minutes"""
    end_time = time.time() + 240
    while time.time() < end_time:
        try:
            # We use 127.0.0.1 to reliably hit the local Docker port
            urllib.request.urlopen("http://127.0.0.1/chaos/error", timeout=1)
        except Exception:
            pass
        # Slowed down slightly so we don't accidentally max out the CPU!
        time.sleep(0.5)

print("\n🔥 REAL-WORLD SCENARIO: CASCADING 500 ERRORS 🔥")
print("Simulating a broken database connection for 4 continuous minutes...")

# Start firing the errors in the background
chaos_thread = threading.Thread(target=fire_errors)
chaos_thread.daemon = True
chaos_thread.start()

print("✅ Chaos thread active. 500 errors are successfully cascading.")
print("🍿 Connecting to SentinelAPI logs...\n")

try:
    # Immediately switch to watching the logs while the background thread does the dirty work!
    subprocess.run(["docker", "compose", "logs", "-f", "sentinel_api"], cwd="..")
except KeyboardInterrupt:
    print("\n🛑 Test aborted.")
    sys.exit(0)