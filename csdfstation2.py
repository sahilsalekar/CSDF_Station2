# csdfstation2.py
import os
import json
import time
import threading
import importlib
from queue import Queue
from typing import List, Optional

import requests
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

# ---- your libs ----
import robot_setup
from dashboard import Dashboard

# Station helper pipelines (adjust names if yours differ)
import balance_check
import qr_check
import in_vial_tray
import qr_place_vial
import qr_pick_vial
import failvial

# PLC QR reader used by retry helper
from plc_qr_seq import plc_qr_seq

# =========================
# Constants / Endpoints
# =========================
TASK_FILE = "tasks.json"

TRAY_API       = "http://localhost:8002/is_tray_ready"   # tray gate for experiments
SEND_VIAL_API  = "http://localhost:8005/send_vial"       # cleanup permission (type 2)

# Node-RED UI endpoints
NODERED_STATUS = "http://127.0.0.1:1880/robot-status"
NODERED_TASK   = "http://127.0.0.1:1880/task-update"
NODERED_WEIGHT = "http://127.0.0.1:1880/weight-update"
NODERED_QR     = "http://127.0.0.1:1880/qr-update"

RID_TO_LETTER = "ABCDEFGH"

# =========================
# App / Globals
# =========================
app = FastAPI()

task_queue = Queue()
lock = threading.Lock()

robot_ready = False
robot_busy = False
client = None
shutdown_flag = False

error_flag = False
error_message = ""

# expose currently running task in /status
current_task = None  # dict like {"type":1,"cid":5,"letter":"C","exp_id":101} or {"type":"INIT_STATION2"}

# Station-2 initiation queue (async trigger from Station-1)
station2_queue = Queue()

# =========================
# Models
# =========================
class Task(BaseModel):
    # Allow 3 or 4 elements: [type, cid, letter] or [type, cid, letter, exp_id]
    task: List

class InitiatePayload(BaseModel):
    note: Optional[str] = None  # optional metadata

# =========================
# Persistence
# =========================
def load_tasks():
    if os.path.exists(TASK_FILE):
        with open(TASK_FILE, "r") as f:
            try:
                tasks = json.load(f)
                for t in tasks:
                    task_queue.put(t)
            except json.JSONDecodeError:
                print("[WARN] tasks.json invalid; starting with empty queue.")

def save_tasks():
    with lock:
        with open(TASK_FILE, "w") as f:
            json.dump(list(task_queue.queue), f, indent=2)

# =========================
# Helpers
# =========================
def set_error(msg: str):
    global error_flag, error_message
    error_flag = True
    error_message = msg
    print(f"[ERROR] {msg}")

def clear_error():
    global error_flag, error_message
    error_flag = False
    error_message = ""

def get_pallet_row_col(letter: str):
    mapping = {
        'A': (1, 1), 'B': (1, 2), 'C': (1, 3), 'D': (1, 4),
        'E': (2, 1), 'F': (2, 2), 'G': (2, 3), 'H': (2, 4),
    }
    return mapping[letter.upper()]

def rid_to_letter(rid_val) -> Optional[str]:
    """
    Normalize rid to pallet letter A–H.
    - If rid is int 0..7 -> map via RID_TO_LETTER
    - If rid is '0'..'7' -> same
    - If rid is 'A'..'H' -> use directly
    """
    if rid_val is None:
        return None
    try:
        idx = int(rid_val)
        if 0 <= idx < len(RID_TO_LETTER):
            return RID_TO_LETTER[idx]
    except (ValueError, TypeError):
        pass
    s = str(rid_val).strip().upper()
    if s in "ABCDEFGH":
        return s
    return None

def is_tray_ready() -> bool:
    try:
        res = requests.get(TRAY_API, timeout=2)
        return res.ok and res.json().get("ready", False)
    except Exception as e:
        print(f"[ERROR] Tray check failed: {e}")
        return False

def requeue_task_local(task):
    task_queue.put(task)
    save_tasks()

def remove_task_local(task):
    temp = list(task_queue.queue)
    try:
        temp.remove(task)
        with lock:
            task_queue.queue.clear()
            for t in temp:
                task_queue.put(t)
            save_tasks()
    except ValueError:
        pass

def _task_exists(task_list, t):
    return any(t == x for x in task_list)

def set_dashboard(status: Optional[str] = None, task_txt: Optional[str] = None,
                  weight: Optional[float] = None, qr: Optional[str] = None):
    try:
        if status is not None:
            requests.post(NODERED_STATUS, json={"status": status}, timeout=1)
        if task_txt is not None:
            requests.post(NODERED_TASK, json={"task": task_txt}, timeout=1)
        if weight is not None:
            requests.post(NODERED_WEIGHT, json={"weight": weight}, timeout=1)
        if qr is not None:
            requests.post(NODERED_QR, json={"qrdata": qr}, timeout=1)
    except Exception:
        pass

# =========================
# QR helper
# =========================
def read_qr_with_retry(max_tries=2, delay=0.5):
    """
    Try reading QR up to `max_tries` times.
    Returns the final qr_data dict from plc_qr_seq().
    Expected shape: {"success": bool, "data": "...", "error": "..."}
    """
    last = None
    for attempt in range(1, max_tries + 1):
        qr_data = plc_qr_seq()
        if qr_data.get("success"):
            return qr_data
        print(f"[WARN] QR scan failed (attempt {attempt}/{max_tries}). "
              f"Error: {qr_data.get('error') or qr_data.get('data')}")
        last = qr_data
        if attempt < max_tries:
            time.sleep(delay)
    return last or {"success": False, "error": "Unknown QR error"}

# =========================
# Startup
# =========================
@app.on_event("startup")
def startup_event():
    global client, robot_ready, robot_busy, current_task

    clear_error()
    robot_ready = False
    robot_busy = True
    current_task = {"type": "STARTUP"}
    set_dashboard(status="busy", task_txt="", weight=0.0, qr="")

    load_tasks()

    print("⚙️  Initializing robot...")
    try:
        client = robot_setup.setup_robot()
        print("✅ Robot setup finished.")
    except Exception as e:
        set_error(f"Robot setup failed: {e}")
        robot_ready = False
        robot_busy = False
        current_task = None
        set_dashboard(status="idle")
        return

    robot_ready = True
    robot_busy = False
    current_task = None
    set_dashboard(status="idle")

    threading.Thread(target=keep_robot_alive_loop, daemon=True).start()
    threading.Thread(target=dispatcher_loop, daemon=True).start()

# =========================
# Background loops
# =========================
def keep_robot_alive_loop():
    global robot_busy, client, shutdown_flag
    while not shutdown_flag:
        try:
            if client is not None and not robot_busy:
                client.SendCommand("attach 1")
        except Exception as e:
            set_error(f"Keep-alive failed: {e}")
        time.sleep(600)  # every 10 minutes

def dispatcher_loop():
    """
    Continuously:
      1) Execute tasks from file queue (type 1 or 2).
      2) Handle Station-2 initiation triggers (balance + QR + enqueue experiment task with exp_id.
         If no match or scan fails: pick & fail vial at QR).
    """
    global robot_busy

    while not shutdown_flag:
        try:
            if not task_queue.empty() and not robot_busy:
                t = task_queue.get()
                save_tasks()
                process_task(t)
                continue

            if not station2_queue.empty() and not robot_busy:
                payload = station2_queue.get()
                run_station2_initiation(payload)
                continue

            time.sleep(2)

        except Exception as e:
            set_error(f"dispatcher_loop: {e}")
            time.sleep(2)

# =========================
# Task processing (executor semantics + exp_id support)
# =========================
def process_task(task):
    """
    task shapes:
      - [task_type, cid, letter]
      - [task_type, cid, letter, exp_id]
    - type=1 (experiment) => tray gate
    - type=2 (cleanup)    => SEND_VIAL gate
    """
    global robot_busy, client, current_task

    if not robot_ready or client is None:
        print("⛔ Robot not ready; requeuing task.")
        requeue_task_local(task)
        time.sleep(1)
        return

    if not isinstance(task, list) or len(task) < 3:
        set_error(f"Invalid task format (skipping): {task}")
        return

    task_type = task[0]
    cid       = task[1]
    col_letter= task[2]
    exp_id    = task[3] if len(task) >= 4 else None

    robot_busy = True
    current_task = {"type": task_type, "cid": cid, "letter": col_letter}
    if exp_id is not None:
        current_task["exp_id"] = exp_id

    task_txt = f"{task_type} {cid} {col_letter}" + (f" exp_id={exp_id}" if exp_id is not None else "")
    set_dashboard(status="busy", task_txt=task_txt)

    try:
        if task_type == 2:
            try:
                resp = requests.get(SEND_VIAL_API, timeout=5)
                if not resp.ok or not resp.json().get("sendvial"):
                    print("⛔ Cleanup blocked. Requeueing.")
                    requeue_task_local(task)
                    return
            except Exception as e:
                set_error(f"Cleanup permission check failed: {e}")
                requeue_task_local(task)
                return

        if task_type == 1 and not is_tray_ready():
            print("🟥 Tray not ready — requeueing experiment.")
            requeue_task_local(task)
            return

        print(f"🚀 Running task: {task}")
        row, col = get_pallet_row_col(col_letter)
        module = importlib.import_module(f"{task_type}Station{cid}")

        # Try to pass exp_id if available; fallback to 3-arg signature
        if exp_id is not None:
            try:
                module.run(client, row, col, exp_id)
            except TypeError:
                module.run(client, row, col)
        else:
            module.run(client, row, col)

        print(f"✅ Task completed: {task}")
        remove_task_local(task)

    except Exception as e:
        set_error(f"Task execution failed: {e}")
        requeue_task_local(task)
    finally:
        robot_busy = False
        current_task = None
        set_dashboard(status="idle", task_txt="", weight=0.0, qr="")

# =========================
# Station-2 initiation:
# Balance + QR + Place-at-QR + Scan → If found: enqueue [1, cid, letter, exp_id]
# If not found / scan fail: qr_pick_vial + failvial, then exit.
# =========================
def run_station2_initiation(payload: dict):
    global robot_busy, client, current_task

    if not robot_ready or client is None:
        print("⛔ Robot not ready; aborting Station-2 initiation.")
        return

    dash = Dashboard()
    robot_busy = True
    current_task = {"type": "INIT_STATION2"}
    set_dashboard(status="busy", task_txt="INIT_STATION2")

    try:
        # Balance check (keep if needed in your workflow)
        balance_check.balance_check(client)
        time.sleep(0.5)

        # QR check
        print("Executing qr_check")
        qr_check.qr_check(client)
        time.sleep(0.5)

        # In vial tray
        print("Executing in_vial_tray")
        if not in_vial_tray.in_vial_tray(client):
            return
        time.sleep(0.5)

        # QR place vial at the scanner
        print("Executing qr_place_vial")
        qr_place_vial.qr_place_vial(client)

        # Read QR with retry
        print("Executing qr plc sequence")
        qr_data = read_qr_with_retry(max_tries=2, delay=0.5)

        if qr_data.get("success"):
            print(f"Scan Okay: {qr_data['data']}")
            vial_id = qr_data['data']
            set_dashboard(qr=str(vial_id))

            # dashboard lookup with NEW SCHEMA
            exp_response = dash.get_experiment_id(vial_id)
            # {
            #   "found": bool,
            #   "ready": bool | None,
            #   "exp": { "exp_id": int, "cid": int | None, "rid": str | None } | None,
            #   "message": str
            # }

            if exp_response and exp_response.get("found"):
                exp = exp_response.get("exp") or {}
                exp_id = exp.get("exp_id")
                cid = exp.get("cid")
                rid_val = exp.get("rid")

                print(f"Experiment found for vial {vial_id}: exp_id={exp_id}, cid={cid}, rid={rid_val}")

                letter = rid_to_letter(rid_val)
                if not letter:
                    # invalid rid → pick & fail to clear QR station
                    set_error(f"Invalid rid from experiment lookup: {rid_val}")
                    print("Executing qr_pick_vial (invalid rid)")
                    qr_pick_vial.qr_pick_vial(client)
                    time.sleep(0.5)
                    print("Executing fail vial (invalid rid)")
                    failvial.failvial(client)
                    return

                # ENQUEUE experiment task with exp_id (do not execute immediately)
                new_task = [1, cid, letter, exp_id]
                task_queue.put(new_task)
                save_tasks()
                print(f"🧪 Enqueued experiment task: {new_task}")

                # NOTE: we intentionally DO NOT pick here on success
                # 1Station{cid} will handle presence check and pick from QR if reactor empty

            else:
                # Not found → pick & fail
                print(f"No experiment found for vial {vial_id}. Picking and failing vial.")
                print("Executing qr_pick_vial")
                qr_pick_vial.qr_pick_vial(client)
                time.sleep(0.5)
                print("Executing fail vial")
                failvial.failvial(client)
                return

        else:
            # Scan failed → pick & fail (clear QR station)
            print(f"Scan Failed: {qr_data.get('data')}, Error: {qr_data.get('error')}")
            print("Executing qr_pick_vial (scan fail)")
            qr_pick_vial.qr_pick_vial(client)
            time.sleep(0.5)
            print("Executing fail vial (scan fail)")
            failvial.failvial(client)
            return

    except Exception as e:
        set_error(f"Station-2 initiation failed: {e}")
    finally:
        robot_busy = False
        current_task = None
        set_dashboard(status="idle", task_txt="", weight=0.0, qr="")

# =========================
# API endpoints
# =========================
@app.get("/csdfstation2_status")
def status():
    dash = Dashboard()
    cryst = dash.get_crystallines_online()

    # Figure out crystalline state
    status_message = ""
    crystalline_any_on = False
    crystalline_off_list = []

    if cryst and isinstance(cryst, dict):
        crystalline_any_on = any(bool(v) for v in cryst.values())
        crystalline_off_list = [str(k) for k, v in cryst.items() if not bool(v)]
        if not crystalline_any_on:
            status_message = "All crystallines are offline."
        elif crystalline_off_list:
            status_message = f"Crystallines offline: {', '.join(crystalline_off_list)}."
    else:
        status_message = "Could not read crystallines status."

    # Overall ready = robot ready + at least one crystalline online
    ready_overall = bool(robot_ready) and crystalline_any_on
    if not robot_ready:
        status_message = "Robot not ready."

    return {
        "ready": ready_overall,
        "busy": robot_busy,
        "error": error_flag,
        "status_message": status_message,
        "current_task": current_task,
    }

@app.post("/initiate-station2")
def initiate_station2(payload: InitiatePayload):
    station2_queue.put(payload.dict())
    return {"status": "Initiation queued"}

# File-backed task endpoints (both types allowed; type 1 may or may not include exp_id)
@app.post("/add_task")
def add_task(task: Task):
    if not isinstance(task.task, list) or len(task.task) < 3:
        return {"status": "Invalid task format. Expected [type, cid, letter, (optional exp_id)].", "task": task.task}
    current = list(task_queue.queue)
    if _task_exists(current, task.task):
        return {"status": "Task already exists", "task": task.task}
    task_queue.put(task.task)
    save_tasks()
    return {"status": "Task added", "task": task.task}

@app.get("/next_task")
def get_next_task():
    if not task_queue.empty():
        t = task_queue.get()
        save_tasks()
        return {"task": t}
    return {"task": None}

@app.get("/queue")
def get_queue():
    return {"queue": list(task_queue.queue)}

@app.get("/tasks")
def get_tasks():
    return {"tasks": list(task_queue.queue)}

@app.post("/requeue_task")
def requeue_task(task: Task):
    task_queue.put(task.task)
    save_tasks()
    return {"status": "Task requeued", "task": task.task}

@app.post("/remove_task")
def remove_task(task: Task):
    temp = list(task_queue.queue)
    try:
        temp.remove(task.task)
        with lock:
            task_queue.queue.clear()
            for t in temp:
                task_queue.put(t)
            save_tasks()
        return {"status": "Task removed", "task": task.task}
    except ValueError:
        return {"status": "Task not found in queue", "task": task.task}

# =========================
# Entrypoint
# =========================
if __name__ == "__main__":
    uvicorn.run("csdfstation2:app", host="0.0.0.0", port=8000, reload=True)
