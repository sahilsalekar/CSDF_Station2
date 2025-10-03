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
INITIATE_FILE = "initiate_task.json"  # persistent queue for Station-1 initiation triggers

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
# IMPORTANT: use RLock to avoid deadlocks when nested functions acquire the same lock
lock = threading.RLock()

robot_ready = False
robot_busy = False
client = None
shutdown_flag = False

error_flag = False
error_message = ""

# expose currently running task in /status
# use key "rid" with LETTER value A..H
current_task = None  # dict like {"type":1,"cid":5,"rid":"C","exp_id":101} or {"type":"INIT_STATION2"}

# legacy in-memory (kept for compatibility; logic uses INITIATE_FILE)
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
# Persistence: tasks.json
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
# Persistence: initiate_task.json
# =========================
def _read_initiate_list() -> List[dict]:
    with lock:
        if not os.path.exists(INITIATE_FILE):
            with open(INITIATE_FILE, "w") as f:
                json.dump([], f)
            return []
        try:
            with open(INITIATE_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return []
        except Exception:
            print("[WARN] initiate_task.json unreadable; resetting to empty list.")
            with open(INITIATE_FILE, "w") as f:
                json.dump([], f)
            return []

def _write_initiate_list(items: List[dict]) -> None:
    with lock:
        with open(INITIATE_FILE, "w") as f:
            json.dump(items, f, indent=2)

def enqueue_initiate(payload: dict) -> None:
    items = _read_initiate_list()
    items.append(payload or {})
    _write_initiate_list(items)

def pop_next_initiate() -> Optional[dict]:
    items = _read_initiate_list()
    if not items:
        return None
    nxt = items.pop(0)
    _write_initiate_list(items)
    return nxt

def has_initiate() -> bool:
    items = _read_initiate_list()
    return len(items) > 0

# =========================
# Helpers
# =========================
def set_error(msg: str):
    global error_flag, error_message
    error_flag = True
    error_message = msg
    print(f"[ERROR] {msg}", flush=True)

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
    if rid_val is None:
        return None
    s = str(rid_val).strip().upper()

    # exact single letter A..H
    if len(s) == 1 and s in RID_TO_LETTER:
        return s

    # pure integer 0..7
    if s.isdigit():
        try:
            idx = int(s)
            if 0 <= idx < len(RID_TO_LETTER):
                return RID_TO_LETTER[idx]
        except ValueError:
            pass

    # pick first A..H found anywhere (handles "A42", "B-1", etc.)
    for ch in s:
        if ch in RID_TO_LETTER:
            return ch

    # optional: if string starts with single digit 0..7, map that
    if s and s[0] in "01234567":
        return RID_TO_LETTER[int(s[0])]

    return None

def is_tray_ready() -> bool:
    try:
        res = requests.get(TRAY_API, timeout=2)
        return res.ok and res.json().get("ready", False)
    except Exception as e:
        print(f"[WARN] Tray check failed: {e}", flush=True)
        return False

def requeue_task_local(task):
    task_queue.put(task)
    save_tasks()

def remove_task_local(task):
    # Not used in the current flow, but make it safe with RLock
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

# Queue helpers: priority handling for initiation-created experiment tasks
def enqueue_priority_task(task):
    """
    Put `task` at the FRONT of the queue (priority), removing any duplicate.
    Persist the new order to tasks.json.
    """
    with lock:
        q = list(task_queue.queue)
        try:
            q.remove(task)  # avoid duplicates
        except ValueError:
            pass
        q.insert(0, task)  # put at front
        task_queue.queue.clear()
        for t in q:
            task_queue.put(t)
    # save OUTSIDE the lock to avoid nested-lock deadlocks
    save_tasks()
    print(f"[DEBUG] enqueue_priority_task -> queued at front: {task}", flush=True)

def pop_next_task_priority():
    """
    Pop a priority task first if present.
    Priority rule: type==1 AND exp_id present (len>=4) — i.e., tasks created by initiation.
    Otherwise, pop the head of the queue.
    IMPORTANT: does NOT call save_tasks(); we keep the task in tasks.json until success.
    """
    with lock:
        q = list(task_queue.queue)
        if not q:
            return None

        pri_idx = None
        for i, t in enumerate(q):
            if isinstance(t, list) and len(t) >= 4 and t[0] == 1:
                pri_idx = i
                break

        if pri_idx is None:
            task = q.pop(0)
        else:
            task = q.pop(pri_idx)

        task_queue.queue.clear()
        for x in q:
            task_queue.put(x)
        # Do NOT save here — keep task in file until success
        print(f"[DEBUG] pop_next_task_priority -> popped: {task}", flush=True)
        return task

# Helper: check if any type-2 task exists in the queue (anywhere)
def queue_has_type2() -> bool:
    with lock:
        return any(isinstance(t, list) and len(t) >= 1 and t[0] == 2 for t in list(task_queue.queue))
    
def queue_has_priority_task() -> bool:
    with lock:
        return any(isinstance(t, list) and len(t) >= 4 and t[0] == 1 for t in list(task_queue.queue))


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
              f"Error: {qr_data.get('error') or qr_data.get('data')}", flush=True)
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

    print("⚙️  Initializing robot...", flush=True)
    try:
        client = robot_setup.setup_robot()
        print("✅ Robot setup finished.", flush=True)
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
            # Avoid flipping error flag during runs; only raise when idle
            if not robot_busy:
                set_error(f"Keep-alive failed: {e}")
            else:
                print(f"[WARN] Keep-alive failed while busy: {e}", flush=True)
        time.sleep(600)  # every 10 minutes

def dispatcher_loop():
    """
    Policy:
      - If there is an initiation task and NO type-2 task anywhere in the queue, run initiation first.
      - Otherwise, execute tasks from file queue (type 1 or 2), prioritizing initiation-created experiment tasks.
      - When a type-2 is blocked, initiation is triggered inside process_task and the gate is re-checked.
    """
    global robot_busy

    while not shutdown_flag:
        try:
            if not robot_busy:
                # Priority: initiation when no type-2 tasks exist
                if has_initiate() and not queue_has_type2():
                    payload = pop_next_initiate()
                    if payload:
                        run_station2_initiation(payload)
                        time.sleep(0.5)
                        continue

                # Pop next task (priority-aware: initiation-created experiments first)
                t = pop_next_task_priority()
                if t is not None:
                    process_task(t)
                    time.sleep(0.2)
                    continue

            time.sleep(1.0)

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
    - type=1 (experiment) => tray gate (optional)
    - type=2 (cleanup)    => SEND_VIAL gate
    Failure handling:
      - On failure (exception): DO NOT requeue; persist removal via save_tasks().
      - On cleanup blocked: requeue and save (retry later).
    """
    global robot_busy, client, current_task, error_flag, error_message

    if not robot_ready or client is None:
        print("⛔ Robot not ready; requeuing task.", flush=True)
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

    allow_cleanup = None  # sentinel; only meaningful for task_type == 2


    # ---- reset error state BEFORE starting the task ----
    error_flag = False
    error_message = None
    # ----------------------------------------------------

    robot_busy = True
    # Status key must be 'rid' but value is the LETTER (A..H)
    current_task = {"type": task_type, "cid": cid, "rid": col_letter}
    if exp_id is not None:
        current_task["exp_id"] = exp_id

    task_txt = f"{task_type} {cid} {col_letter}" + (f" exp_id={exp_id}" if exp_id is not None else "")
    set_dashboard(status="busy", task_txt=task_txt)

    try:
        if task_type == 2:
            # Check cleanup gate (treat network issues as warnings to keep error clear during run)
            try:
                resp = requests.get(SEND_VIAL_API, timeout=5)
                allow_cleanup = resp.ok and resp.json().get("sendvial")
            except Exception as e:
                print(f"[WARN] Cleanup permission check failed: {e}", flush=True)
                allow_cleanup = False

        if not allow_cleanup:
            print("⛔ Cleanup blocked.", flush=True)
            # If there's an initiation, run one now
            payload = pop_next_initiate()
            if payload:
                print("[INFO] Running Station-2 initiation due to blocked cleanup.", flush=True)
                saved_task = current_task
                saved_busy = robot_busy
                try:
                    run_station2_initiation(payload)
                finally:
                    robot_busy = saved_busy
                    current_task = saved_task

                # >>> PREEMPT: if initiation enqueued a priority task, yield and let it run first
                if queue_has_priority_task():
                    print("[INFO] Priority experiment enqueued; deferring current type-2.", flush=True)
                    requeue_task_local(task)   # move current cleanup to the end
                    return

            # No (or failed) initiation → re-check the cleanup gate
            try:
                resp2 = requests.get(SEND_VIAL_API, timeout=5)
                allow_cleanup = resp2.ok and resp2.json().get("sendvial")
            except Exception as e:
                print(f"[WARN] Cleanup permission re-check failed: {e}", flush=True)
                allow_cleanup = False

            if not allow_cleanup:
                # Still blocked -> requeue and exit (task stays in tasks.json)
                requeue_task_local(task)
                return
        # else: fall through to execute this type-2 now


        # Optional experiment tray gate:
        # if task_type == 1 and not is_tray_ready():
        #     print("🟥 Tray not ready — requeueing experiment.", flush=True)
        #     requeue_task_local(task)
        #     return

        print(f"🚀 Running task: {task}", flush=True)
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

        print(f"✅ Task completed: {task}", flush=True)
        # Persist the fact that we consumed the task ONLY AFTER success
        save_tasks()

    except Exception as e:
        # On failure, DO NOT requeue; remove it by saving current queue state
        set_error(f"Task execution failed: {e}")
        save_tasks()
    finally:
        robot_busy = False
        current_task = None
        set_dashboard(status="idle", task_txt="", weight=0.0, qr="")

# =========================
# Station-2 initiation:
# Balance + QR + Place-at-QR + Scan → If found: enqueue [1, cid, letter, exp_id] (PRIORITY)
# If not found / scan fail: qr_pick_vial + failvial, then exit.
# =========================
def run_station2_initiation(payload: dict):
    global robot_busy, client, current_task, error_flag, error_message

    if not robot_ready or client is None:
        print("⛔ Robot not ready; aborting Station-2 initiation.", flush=True)
        return

    # Clear stale error during initiation, too
    error_flag = False
    error_message = None

    dash = Dashboard()
    robot_busy = True
    current_task = {"type": "INIT_STATION2"}
    set_dashboard(status="busy", task_txt="INIT_STATION2")

    try:
        # Balance check (keep if needed in your workflow)
        balance_check.balance_check(client)
        time.sleep(0.5)

        # QR check
        print("Executing qr_check", flush=True)
        qr_check.qr_check(client)
        time.sleep(0.5)

        # In vial tray
        print("Executing in_vial_tray", flush=True)
        if not in_vial_tray.in_vial_tray(client):
            return
        time.sleep(0.5)

        # QR place vial at the scanner
        print("Executing qr_place_vial", flush=True)
        qr_place_vial.qr_place_vial(client)

        # Read QR with retry
        print("Executing qr plc sequence", flush=True)
        qr_data = read_qr_with_retry(max_tries=2, delay=0.5)

        if qr_data.get("success"):
            print(f"Scan Okay: {qr_data['data']}", flush=True)
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

                print(f"Experiment found for vial {vial_id}: exp_id={exp_id}, cid={cid}, rid={rid_val}", flush=True)

                letter = rid_to_letter(rid_val)
                print(f"[DEBUG] rid raw={rid_val!r} -> letter={letter!r}", flush=True)
                if not letter:
                    # invalid rid → pick & fail to clear QR station
                    set_error(f"Invalid rid from experiment lookup: {rid_val}")
                    print("Executing qr_pick_vial (invalid rid)", flush=True)
                    qr_pick_vial.qr_pick_vial(client)
                    time.sleep(0.5)
                    print("Executing fail vial (invalid rid)", flush=True)
                    failvial.failvial(client)
                    return

                # ENQUEUE experiment task with exp_id (PRIORITY at front)
                new_task = [1, cid, letter, exp_id]
                enqueue_priority_task(new_task)
                print(f"🧪 Enqueued PRIORITY experiment task: {new_task}", flush=True)

                # Make robot home Pos
                client.SendCommand("movej 1 1017.83 -2.902 180.537 178.063 103.542 999.837")
                reply = client.SendCommand("waitforeom")

                # NOTE: we intentionally DO NOT pick here on success
                # 1Station{cid} will handle presence check and pick from QR if reactor empty

            else:
                # Not found → pick & fail
                print(f"No experiment found for vial {vial_id}. Picking and failing vial.", flush=True)
                print("Executing qr_pick_vial", flush=True)
                qr_pick_vial.qr_pick_vial(client)
                time.sleep(0.5)
                print("Executing fail vial", flush=True)
                failvial.failvial(client)
                return

        else:
            # Scan failed → pick & fail (clear QR station)
            print(f"Scan Failed: {qr_data.get('data')}, Error: {qr_data.get('error')}", flush=True)
            print("Executing qr_pick_vial (scan fail)", flush=True)
            qr_pick_vial.qr_pick_vial(client)
            time.sleep(0.5)
            print("Executing fail vial (scan fail)", flush=True)
            failvial.failvial(client)
            return

    except Exception as e:
        set_error(f"Station-2 initiation failed: {e}")
    finally:
        #Home position
        client.SendCommand("movej 1 1017.83 -2.902 180.537 178.063 103.542 -934.686")
        reply = client.SendCommand("waitforeom")
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
        "error_message": error_message if error_flag else None,
        "status_message": status_message,
        "current_task": current_task,                   # {"type":..., "cid":..., "rid": "A".. "H", ...}
        "initiate_queue_len": len(_read_initiate_list())  # for visibility
    }

@app.post("/initiate-station2")
def initiate_station2(payload: InitiatePayload):
    # Persist the initiation request
    enqueue_initiate(payload.dict())
    return {"status": "Initiation queued (persistent)"}

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
        # This endpoint keeps legacy behavior and persists removal immediately
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
