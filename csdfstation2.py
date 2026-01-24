# CSDFStation2.py
import os
import json
import time
import threading
import importlib
from typing import Any, Dict, List, Optional, Union

import requests
from fastapi import FastAPI
from pydantic import BaseModel, Field
import uvicorn

# ---- your libs ----
import robot_setup
from dashboard import Dashboard

# Station helper pipelines (adjust names if yours differ)
from balance import balance_check
from qr import qr_check
import in_vial_tray
from qr import qr_place_vial
from qr import qr_pick_vial
import failvial

# PLC QR reader used by retry helper
from plc_qr_seq import plc_qr_seq


# =========================
# Constants / Endpoints
# =========================
TASK_FILE = "tasks.json"                 # SINGLE source of truth for tasks
INITIATE_FILE = "initiate_task.json"     # persistent queue for Station-1 initiation triggers

TRAY_API       = "http://localhost:8002/is_tray_ready"   # tray gate for experiments (optional)
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


# =========================
# Models
# =========================
class TaskPayload(BaseModel):
    """
    Supports:
      - dict task format (recommended):
          {"type":1,"cid":2,"rid":"A","exp_id":123}
          {"type":2,"cid":5,"rid":"G"}
      - legacy list format (accepted for backward compatibility):
          [1, 2, "A", 123]
          [2, 5, "G"]
    """
    task: Union[Dict[str, Any], List[Any]]


class InitiatePayload(BaseModel):
    note: Optional[str] = None  # optional metadata


# =========================
# Persistence: tasks.json (SINGLE source of truth)
# =========================
def _ensure_file(path: str, default_json: Any) -> None:
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(default_json, f, indent=2)


def _atomic_write_json(path: str, data: Any) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)  # atomic replace


def _read_json_list(path: str) -> List[Any]:
    _ensure_file(path, [])
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        # reset corrupted file safely
        _atomic_write_json(path, [])
        return []


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


def normalize_task(item: Union[Dict[str, Any], List[Any]]) -> Optional[Dict[str, Any]]:
    """
    Normalizes task into keyword dict format:
      {"type": int, "cid": int, "rid": "A".."H", "exp_id": optional int}
    Also supports your "status json" style:
      {"exp_id": 1609, "cid": 2, "rid": 0}  -> becomes {"type":1,"cid":2,"rid":"A","exp_id":1609}
    """
    # dict input
    if isinstance(item, dict):
        # status-style (no "type", rid numeric)
        if "type" not in item and "exp_id" in item and "cid" in item and "rid" in item:
            letter = rid_to_letter(item.get("rid"))
            if not letter:
                return None
            return {
                "type": 1,
                "cid": int(item["cid"]),
                "rid": letter,
                "exp_id": int(item["exp_id"]),
            }

        # recommended task style
        if "type" in item and "cid" in item and "rid" in item:
            ttype = int(item["type"])
            cid = int(item["cid"])
            letter = rid_to_letter(item.get("rid"))
            if not letter:
                return None

            out = {"type": ttype, "cid": cid, "rid": letter}
            if "exp_id" in item and item["exp_id"] is not None:
                out["exp_id"] = item["exp_id"]   # keep as-is (string or int)
            return out

        return None

    # legacy list input
    if isinstance(item, list) and len(item) >= 3:
        try:
            ttype = int(item[0])
            cid = int(item[1])
            letter = rid_to_letter(item[2])
            if not letter:
                return None

            out = {"type": ttype, "cid": cid, "rid": letter}
            if len(item) >= 4 and item[3] is not None:
                out["exp_id"] = item[3]  # keep as-is
            return out
        except Exception:
            return None

    return None


def read_tasks() -> List[Dict[str, Any]]:
    """
    Reads tasks.json and normalizes everything to dict-based tasks.
    If the file contains status-style objects (exp_id,cid,rid int), they become type-1 tasks.
    If legacy list tasks exist, they become dict tasks.
    """
    with lock:
        raw = _read_json_list(TASK_FILE)
        normalized: List[Dict[str, Any]] = []
        changed = False

        for item in raw:
            nt = normalize_task(item)
            if nt is None:
                # skip invalid entries (but mark changed so we rewrite cleanly)
                changed = True
                continue
            normalized.append(nt)
            if nt != item:
                changed = True

        # If we normalized/cleaned anything, rewrite in canonical format
        if changed:
            _atomic_write_json(TASK_FILE, normalized)

        return normalized


def write_tasks(tasks: List[Dict[str, Any]]) -> None:
    with lock:
        _atomic_write_json(TASK_FILE, tasks)


def task_equals(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    # strict equality on keys used by the system
    keys = set(a.keys()) | set(b.keys())
    for k in keys:
        if a.get(k) != b.get(k):
            return False
    return True


def task_exists(tasks: List[Dict[str, Any]], t: Dict[str, Any]) -> bool:
    return any(task_equals(x, t) for x in tasks)


def enqueue_task(t: Dict[str, Any]) -> None:
    tasks = read_tasks()
    if task_exists(tasks, t):
        return
    tasks.append(t)
    write_tasks(tasks)


def enqueue_priority_task(t: Dict[str, Any]) -> None:
    """
    Put task at the FRONT of tasks.json, removing any duplicate.
    """
    tasks = read_tasks()
    tasks = [x for x in tasks if not task_equals(x, t)]
    tasks.insert(0, t)
    write_tasks(tasks)
    print(f"[DEBUG] enqueue_priority_task -> queued at front: {t}", flush=True)


def remove_task_from_file(t: Dict[str, Any]) -> None:
    tasks = read_tasks()
    new_tasks: List[Dict[str, Any]] = []
    removed = False
    for x in tasks:
        if not removed and task_equals(x, t):
            removed = True
            continue
        new_tasks.append(x)
    if removed:
        write_tasks(new_tasks)


def queue_has_type2(tasks: List[Dict[str, Any]]) -> bool:
    return any(x.get("type") == 2 for x in tasks)


def queue_has_type1(tasks: List[Dict[str, Any]]) -> bool:
    return any(x.get("type") == 1 for x in tasks)


def queue_has_priority_task(tasks: List[Dict[str, Any]]) -> bool:
    # priority: experiment tasks created by initiation (has exp_id)
    return any(x.get("type") == 1 and "exp_id" in x for x in tasks)


def select_next_task(tasks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Priority rule:
      - First experiment task with exp_id (type=1 AND has exp_id)
      - Else first in file order
    """
    for x in tasks:
        if x.get("type") == 1 and "exp_id" in x:
            return x
    return tasks[0] if tasks else None


def bring_any_type1_to_front() -> Optional[Dict[str, Any]]:
    """
    When cleanup is blocked (sendvial false), search tasks.json for ANY type-1.
    If found, move it to the front and persist.
    Returns the moved task or None.
    """
    tasks = read_tasks()
    if not tasks:
        return None

    idx = None
    # prefer priority experiment (has exp_id) first
    for i, t in enumerate(tasks):
        if t.get("type") == 1 and "exp_id" in t:
            idx = i
            break
    # else any type 1
    if idx is None:
        for i, t in enumerate(tasks):
            if t.get("type") == 1:
                idx = i
                break

    if idx is None:
        return None

    t = tasks.pop(idx)
    tasks.insert(0, t)
    write_tasks(tasks)
    print(f"[INFO] Cleanup blocked -> moved type-1 to front: {t}", flush=True)
    return t


# =========================
# Persistence: initiate_task.json (unchanged, file-backed)
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
        _atomic_write_json(INITIATE_FILE, items)


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


def is_tray_ready() -> bool:
    try:
        res = requests.get(TRAY_API, timeout=2)
        return res.ok and res.json().get("ready", False)
    except Exception as e:
        print(f"[WARN] Tray check failed: {e}", flush=True)
        return False


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

    # Ensure files exist (no in-memory queue load)
    _ensure_file(TASK_FILE, [])
    _ensure_file(INITIATE_FILE, [])

    # Normalize tasks.json immediately (supports your status-json format too)
    _ = read_tasks()

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
    Policy (file-only tasks.json):
      - ALWAYS prefer finishing tasks already in tasks.json first.
      - Initiation is only run when:
          (a) tasks.json has no tasks, OR
          (b) cleanup is blocked and we try initiation as a way to produce a priority experiment.
      - Task selection is priority-aware:
          type==1 AND has exp_id -> first
          else first task in file

    Extra condition:
      - If we select a type-2 (cleanup) and sendvial is false:
          bring any type-1 in tasks.json to the front (priority) and run that first.
          Then continue normally.
    """
    global robot_busy, shutdown_flag

    while not shutdown_flag:
        try:
            if robot_busy:
                time.sleep(0.5)
                continue

            tasks = read_tasks()

            # 1) If there are tasks in file -> process them first
            if tasks:
                t = select_next_task(tasks)
                if t is not None:
                    # if cleanup is blocked, bring type-1 to front and try again
                    if t.get("type") == 2:
                        allow_cleanup = False
                        try:
                            resp = requests.get(SEND_VIAL_API, timeout=5)
                            allow_cleanup = resp.ok and resp.json().get("sendvial", False)
                        except Exception as e:
                            print(f"[WARN] Cleanup permission check failed: {e}", flush=True)
                            allow_cleanup = False

                        if not allow_cleanup:
                            # NEW RULE: if sendvial false, move any type-1 to front (if exists)
                            moved = bring_any_type1_to_front()
                            if moved is not None:
                                # Let loop re-read and execute type-1 next
                                time.sleep(0.2)
                                continue

                            # No type-1 found -> try initiation if any
                            if has_initiate():
                                payload = pop_next_initiate()
                                if payload:
                                    print("[INFO] Running Station-2 initiation due to blocked cleanup (no type-1 in tasks).", flush=True)
                                    run_station2_initiation(payload)
                                    time.sleep(0.2)
                                    continue

                            # Still blocked and nothing else to do
                            time.sleep(1.0)
                            continue

                    # Execute the selected task (remove from file only after outcome)
                    process_task(t)
                    time.sleep(0.2)
                    continue

            # 2) No tasks.json tasks -> initiation allowed (same idea as before)
            if has_initiate():
                payload = pop_next_initiate()
                if payload:
                    run_station2_initiation(payload)
                    time.sleep(0.5)
                    continue

            time.sleep(1.0)

        except Exception as e:
            set_error(f"dispatcher_loop: {e}")
            time.sleep(2)


# =========================
# Task processing (file-based tasks.json)
# =========================
def process_task(task: Dict[str, Any]):
    """
    task dict shapes:
      - {"type": 1, "cid": int, "rid": "A".."H"}  (exp_id optional)
      - {"type": 2, "cid": int, "rid": "A".."H"}

    File semantics:
      - Task remains in tasks.json until:
          - SUCCESS -> we remove it from file
          - EXECUTION EXCEPTION -> we remove it from file (matches your prior behavior: do not requeue)
      - Cleanup blocked:
          - we do not remove it; we just defer it (dispatcher decides what to do next)
    """
    global robot_busy, client, current_task, error_flag, error_message, robot_ready

    if not robot_ready or client is None:
        print("⛔ Robot not ready; will retry later (task stays in file).", flush=True)
        time.sleep(1)
        return

    nt = normalize_task(task)
    if nt is None:
        set_error(f"Invalid task format (removing from file): {task}")
        remove_task_from_file(task)
        return

    task_type = nt["type"]
    cid = nt["cid"]
    col_letter = nt["rid"]
    exp_id = nt.get("exp_id")

    # ---- reset error state BEFORE starting the task ----
    error_flag = False
    error_message = None
    # ----------------------------------------------------

    robot_busy = True
    current_task = {"type": task_type, "cid": cid, "rid": col_letter}
    if exp_id is not None:
        current_task["exp_id"] = exp_id

    task_txt = f"{task_type} {cid} {col_letter}" + (f" exp_id={exp_id}" if exp_id is not None else "")
    set_dashboard(status="busy", task_txt=task_txt)

    try:
        # Cleanup gate check is handled in dispatcher (so we don't duplicate too much),
        # but keep a last-guard here as well.
        if task_type == 2:
            allow_cleanup = False
            try:
                resp = requests.get(SEND_VIAL_API, timeout=5)
                allow_cleanup = resp.ok and resp.json().get("sendvial", False)
            except Exception as e:
                print(f"[WARN] Cleanup permission check failed: {e}", flush=True)
                allow_cleanup = False

            if not allow_cleanup:
                print("⛔ Cleanup blocked (process_task guard). Task stays in file.", flush=True)
                return

        # Optional experiment tray gate (keep commented if you want)
        # if task_type == 1 and not is_tray_ready():
        #     print("🟥 Tray not ready — experiment stays in file.", flush=True)
        #     return

        print(f"🚀 Running task: {nt}", flush=True)
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

        print(f"✅ Task completed: {nt}", flush=True)
        # Remove from file ONLY AFTER success
        remove_task_from_file(nt)

    except Exception as e:
        # On failure, DO NOT requeue (matches your current behavior)
        set_error(f"Task execution failed: {e}")
        remove_task_from_file(nt)

    finally:
        robot_busy = False
        current_task = None
        set_dashboard(status="idle", task_txt="", weight=0.0, qr="")


# =========================
# Station-2 initiation:
# Balance + QR + Place-at-QR + Scan → If found: enqueue {"type":1,"cid":..,"rid":..,"exp_id":..} (PRIORITY)
# If not found / scan fail: qr_pick_vial + failvial, then exit.
# =========================
def run_station2_initiation(payload: dict):
    global robot_busy, client, current_task, error_flag, error_message, robot_ready

    if not robot_ready or client is None:
        print("⛔ Robot not ready; aborting Station-2 initiation.", flush=True)
        return

    # Clear stale error during initiation
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
            vial_id = qr_data["data"]
            set_dashboard(qr=str(vial_id))

            # dashboard lookup with NEW SCHEMA
            exp_response = dash.get_experiment_id(vial_id)
            # expected:
            # {
            #   "found": bool,
            #   "ready": bool | None,
            #   "exp": { "exp_id": int, "cid": int | None, "rid": str|int|None } | None,
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
                new_task = {"type": 1, "cid": int(cid), "rid": letter, "exp_id": int(exp_id)}
                enqueue_priority_task(new_task)
                print(f"🧪 Enqueued PRIORITY experiment task: {new_task}", flush=True)

                # Make robot home Pos
                client.SendCommand("movej 1 1017.83 -2.902 180.537 178.063 103.542 999.837")
                _ = client.SendCommand("waitforeom")

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
        # Home position
        try:
            client.SendCommand("movej 1 1017.83 -2.902 180.537 178.063 103.542 -934.686")
            _ = client.SendCommand("waitforeom")
        except Exception as e:
            print(f"[WARN] Failed to move home in initiation finally: {e}", flush=True)

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
        "current_task": current_task,                    # {"type":..., "cid":..., "rid": "A".. "H", ...}
        "initiate_queue_len": len(_read_initiate_list()), # for visibility
        "tasks_len": len(read_tasks()),
    }


@app.post("/initiate-station2")
def initiate_station2(payload: InitiatePayload):
    enqueue_initiate(payload.dict())
    return {"status": "Initiation queued (persistent)"}


@app.post("/add_task")
def add_task(payload: TaskPayload):
    nt = normalize_task(payload.task)
    if nt is None:
        return {
            "status": "Invalid task format. Expected dict with keys type,cid,rid,(exp_id) "
                      "or legacy list [type,cid,rid,(exp_id)]",
            "task": payload.task
        }

    tasks = read_tasks()
    if task_exists(tasks, nt):
        return {"status": "Task already exists", "task": nt}

    tasks.append(nt)
    write_tasks(tasks)
    return {"status": "Task added", "task": nt}


@app.get("/tasks")
def get_tasks():
    # Always returns canonical dict-based tasks
    return {"tasks": read_tasks()}


@app.get("/queue")
def get_queue():
    # Alias
    return {"queue": read_tasks()}


@app.post("/remove_task")
def remove_task(payload: TaskPayload):
    nt = normalize_task(payload.task)
    if nt is None:
        return {"status": "Invalid task; nothing removed", "task": payload.task}
    remove_task_from_file(nt)
    return {"status": "Task removed (if existed)", "task": nt}


@app.post("/requeue_task")
def requeue_task(payload: TaskPayload):
    nt = normalize_task(payload.task)
    if nt is None:
        return {"status": "Invalid task format; not requeued", "task": payload.task}
    enqueue_task(nt)
    return {"status": "Task requeued (appended if not duplicate)", "task": nt}


@app.get("/next_task")
def get_next_task():
    """
    Kept for legacy visibility. This endpoint DOES NOT remove tasks automatically,
    because tasks.json is the single source of truth and dispatcher is the consumer.
    It simply returns what WOULD be selected next by the priority rule.
    """
    tasks = read_tasks()
    t = select_next_task(tasks)
    return {"task": t}


# =========================
# Entrypoint
# =========================
if __name__ == "__main__":
    uvicorn.run("CSDFStation2:app", host="0.0.0.0", port=8000, reload=True)
