import docker
import subprocess
import sys
import time

print("\n🔥 REAL-WORLD SCENARIO: SUDDEN NODE FAILURE 🔥")
print("Simulating a hard crash of a running container...")

client = docker.from_env()

# Find all running app containers
app_containers = client.containers.list(filters={"label": "com.docker.compose.service=app"})

if not app_containers:
    print("❌ No app containers running. Start the stack first.")
    sys.exit(1)

# Pick the first one and kill it instantly (SIGKILL)
target = app_containers[0]
print(f"💀 Terminating container: {target.name}...")
target.kill()

print("✅ Replica successfully destroyed. Capacity reduced.")
print("🍿 Connecting to SentinelAPI logs to watch the AI recover...\n")

try:
    subprocess.run(["docker", "compose", "logs", "-f", "sentinel_api"], cwd="..")
except KeyboardInterrupt:
    sys.exit(0)