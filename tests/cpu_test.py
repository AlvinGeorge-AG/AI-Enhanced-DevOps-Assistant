import urllib.request
import time
import sys

print("\n🔥 THE 'OLD STUFF' AUTOMATED (V1 DUMB HAMMER) 🔥")
print("Simulating Alvin manually hitting Enter 35 times in a row...\n")

for i in range(1, 36):
    try:
        urllib.request.urlopen("http://localhost/chaos/cpu", timeout=4)
        sys.stdout.write(f"\r   [+] Delivered manual hit #{i}/35... ")
        sys.stdout.flush()
    except Exception:
        pass
    
    # THE MAGIC: 1.5 seconds of total peace so Prometheus can safely enter the open socket and scrape the high CPU!
    time.sleep(1.5)

print("\n\n✅ Manual run simulator finished.")