from fastapi import FastAPI
from pydantic import BaseModel
import json
import os
import threading
import time
import requests
import re

app = FastAPI()

STATUS_FILE = "status.json"
TASK_API = "http://localhost:8000/add_task"
QUEUE_API = "http://localhost:8000/queue"
RID_TO_LETTER = "ABCDEFGH"
lock = threading.Lock()

class StatusUpdate(BaseModel):
    exp_id: str
    cid: int
    rid: int

def load_status():
    if not os.path.exists(STATUS_FILE):
        return []
    try:
        with open(STATUS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_status(data):
    with lock:
        with open(STATUS_FILE, "w") as f:
            json.dump(data, f, indent=2)

def is_valid_status(entry):
    return (
        isinstance(entry.get("cid"), int) and
        isinstance(entry.get("rid"), int) and
        isinstance(entry.get("exp_id"), str) and
        re.match(r"^\d+_\d+$", entry["exp_id"])
    )

def is_task_already_in_queue(task):
    try:
        res = requests.get(QUEUE_API)
        if res.ok:
            queue = res.json().get("queue", [])
            return task in queue
    except Exception as e:
        print(f"[ERROR] Couldn't check task queue: {e}")
    return False

def add_or_update_status(entry):
    if not is_valid_status(entry):
        print(f"[WARNING] Rejected invalid status entry: {entry}")
        return

    data = load_status()
    for i, existing in enumerate(data):
        if existing["exp_id"] == entry["exp_id"]:
            data[i] = entry
            save_status(data)
            print(f"🔁 Updated experiment status: {entry}")
            return

    data.append(entry)
    save_status(data)
    print(f"🆕 Added new experiment status: {entry}")

def check_experiment_completions():
    from dashboard import Dashboard
    dash = Dashboard()

    while True:
        data = load_status()
        updated_status = []

        for entry in data:
            exp_id = entry["exp_id"]
            cid = entry["cid"]
            rid = entry["rid"]

            print(f"🔄 Checking experiment status: {exp_id}")
            try:
                result = dash.check_exp_status(exp_id)
                if result and result.get("is_complete"):
                    print(f"✅ Experiment {exp_id} complete.")
                    letter = RID_TO_LETTER[rid]
                    cleanup_task = [2, cid, letter]
                    if is_task_already_in_queue(cleanup_task):
                        print(f"⚠️ Cleanup task already in queue: {cleanup_task}")
                    else:
                        try:
                            print(f"🧹 Scheduling cleanup task: {cleanup_task}")
                            requests.post(TASK_API, json={"task": cleanup_task})
                        except Exception as e:
                            print(f"[ERROR] Failed to send cleanup task: {e}")
                else:
                    updated_status.append(entry)
            except Exception as e:
                print(f"[ERROR] Failed to check status for {exp_id}: {e}")
                updated_status.append(entry)

        save_status(updated_status)
        time.sleep(120)

@app.post("/update_status")
def update_status(update: StatusUpdate):
    entry = {
        "exp_id": update.exp_id,
        "cid": update.cid,
        "rid": update.rid
    }
    add_or_update_status(entry)
    return {"status": "received"}

@app.get("/status")
def get_status():
    return load_status()

@app.on_event("startup")
def start_background_checker():
    thread = threading.Thread(target=check_experiment_completions, daemon=True)
    thread.start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("status_service:app", host="0.0.0.0", port=8001)
