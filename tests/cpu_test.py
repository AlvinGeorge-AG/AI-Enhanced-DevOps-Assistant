import urllib.request
import subprocess
import sys

print("\n🔥 REAL-WORLD SCENARIO: VIRAL TRAFFIC SURGE 🔥")
print("Simulating a massive CPU spike across the application...")

try:
    # A single request to the chaos endpoint
    urllib.request.urlopen("http://localhost/chaos/cpu", timeout=1)
except Exception:
    pass

print("✅ CPU threads locked at maximum capacity.")
print("🍿 Connecting to SentinelAPI logs...\n")

try:
    # cwd=".." tells Docker Compose to look in the parent folder
    subprocess.run(["docker", "compose", "logs", "-f", "sentinel_api"], cwd="..")
except KeyboardInterrupt:
    print("\n🛑 Test aborted.")
    sys.exit(0)