
import requests
import time

resp = requests.post("http://127.0.0.1:1880/robot-status", json={"status": "busy"}, timeout=1)

print(resp)

time.sleep(5)

resp = requests.post("http://127.0.0.1:1880/robot-status", json={"status": "idle"}, timeout=1)
   