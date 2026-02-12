# import S71200_PLC
# from balance_tcp import BalanceTCPClient
# import time

# S71200_PLC.write_memory_bit(100, 0, True)
# time.sleep(5)
# S71200_PLC.write_memory_bit(100, 0, False)
# time.sleep(1)

# import requests

# payload = {"qrdata": ""}
# resp = requests.post("http://127.0.0.1:1880/qr-update", json=payload, timeout=1)

# from log import write_log

# l = write_log("AS_Test")

# import csdf_kafka
# import time

# csdf_kafka.experiment_started(1, 1, "A")
# time.sleep(10)
# csdf_kafka.experiment_finished(1, 1, "A")

import json
# Add task to status.json
def append_status(exp_id, cid, rid):
    status_file = "status.json"
    try:
        # Load existing data or start fresh
        try:
            with open(status_file, "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = []

        # Append new entry
        data.append({"exp_id": exp_id, "cid": cid, "rid": rid})

        # Write back to file
        with open(status_file, "w") as f:
            json.dump(data, f, indent=2)

        print(f"[📥] Added to status.json: exp_id={exp_id}, cid={cid}, rid={rid}")
    except Exception as e:
        print(f"[ERROR] Failed to write to status.json: {e}")

append_status("1709", 1, 5)