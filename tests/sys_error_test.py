import urllib.request
import subprocess
import sys
import time

print("\n🔥 REAL-WORLD SCENARIO: CASCADING 500 ERRORS 🔥")
print("Simulating a broken database connection / bad code deployment...")

# Rapid-fire 100 broken requests to spike the error rate metric
for i in range(100):
    try:
        urllib.request.urlopen("http://localhost/chaos/error")
    except urllib.error.HTTPError as e:
        if e.code == 500:
            print(f" ➔ [{i+1}/100] User hit a 500 Internal Server Error!")
    except Exception:
        pass
    time.sleep(0.1)

print("✅ Error logs saturated.")
print("🍿 Connecting to SentinelAPI logs...\n")

try:
    subprocess.run(["docker", "compose", "logs", "-f", "sentinel_api"], cwd="..")
except KeyboardInterrupt:
    sys.exit(0)