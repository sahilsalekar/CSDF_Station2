import time
import requests
import importlib
import threading
from dashboard import Dashboard
import robot_setup

# Constants
TASK_API = "http://localhost:8000/next_task"
QUEUE_API = "http://localhost:8000/queue"
ADD_TASK_API = "http://localhost:8000/add_task"
REQUEUE_API = "http://localhost:8000/requeue_task"
REMOVE_API = "http://localhost:8000/remove_task"
TRAY_API = "http://localhost:8002/is_tray_ready"
SEND_VIAL_API = "http://130.159.93.21:8005/send_vial"  

RID_TO_LETTER = "ABCDEFGH"

# Robot state
robot_busy = False


def get_pallet_row_col(letter):
    mapping = {
        'A': (1, 1), 'B': (1, 2), 'C': (1, 3), 'D': (1, 4),
        'E': (2, 1), 'F': (2, 2), 'G': (2, 3), 'H': (2, 4),
    }
    return mapping[letter.upper()]


def is_tray_ready():
    try:
        res = requests.get(TRAY_API)
        return res.ok and res.json().get("ready", False)
    except Exception as e:
        print(f"[ERROR] Tray check failed: {e}")
        return False


def requeue_task(task):
    try:
        requests.post(REQUEUE_API, json={"task": task})
    except Exception as e:
        print(f"[ERROR] Failed to requeue task: {e}")


def remove_task(task):
    try:
        requests.post(REMOVE_API, json={"task": task})
    except Exception as e:
        print(f"[WARN] Could not remove task: {e}")


def process_task(task, client):
    global robot_busy
    time.sleep(0.5)
    resp = requests.post("http://127.0.0.1:1880/robot-status", json={"status": "busy"}, timeout=1)
    time.sleep(0.5)
    task_type, cid, col_letter = task
    robot_busy = True

    payload = {"task": f"{task[0]} {task[1]} {task[2]}"}
    resp = requests.post("http://127.0.0.1:1880/task-update", json=payload, timeout=1)
    try:
        if task_type == 2:
            try:
                resp = requests.get(SEND_VIAL_API, timeout=5)
                if not resp.ok or not resp.json().get("sendvial"):
                    print("⛔ Cleanup blocked. Requeuing task.")
                    requeue_task(task)
                    return
            except Exception as e:
                print(f"[ERROR] Cleanup permission check failed: {e}")
                requeue_task(task)
                return

        if task_type == 1 and not is_tray_ready():
            print("🟥 Tray full — skipping experiment.")
            requeue_task(task)
            return

        print(f"🚀 Running robot task: {task}")
        row, col = get_pallet_row_col(col_letter)
        module = importlib.import_module(f"{task_type}Station{cid}")
        module.run(client, row, col)
        
        # ✅ Only remove task after full success
        print(f"✅ Task completed: {task}")
        remove_task(task)

    except Exception as e:
        print(f"[ERROR] Task execution failed: {e}")

        # ✅ Requeue task to keep it in task.json
        requeue_task(task)

        # Value error exit code
        if isinstance(e, ValueError) and "Unstable or invalid weight" in str(e):
            print("❌ Critical balance error — stopping robot executor.")
            exit(1)

        # ✅ Stop the robot executor if TCS error is critical
        if "TCS error" in str(e):
            print("❌ Fatal TCS error encountered — stopping robot executor.")
            exit(1)  # You can also use sys.exit(1)

    finally:
        robot_busy = False
        time.sleep(0.5)
        resp = requests.post("http://127.0.0.1:1880/robot-status", json={"status": "idle"}, timeout=1)
        time.sleep(0.5)
        payload = {"task": ""}
        resp = requests.post("http://127.0.0.1:1880/task-update", json=payload, timeout=1)
        time.sleep(0.5)
        payload = {"weight": 0.0}
        res = requests.post("http://127.0.0.1:1880/weight-update", json=payload, timeout=1)



def schedule_new_experiment():
    dash = Dashboard()

    try:
        tray = requests.get(TRAY_API)
        if not tray.ok or not tray.json().get("ready"):
            print("🟥 Tray is full — not scheduling experiment.")
            return

        exp_reply = dash.check_for_experiments()
        if exp_reply and exp_reply.get("more"):
            free_reply = dash.get_free_reactor()
            if free_reply and free_reply.get("free"):
                cid = free_reply["cid"]
                rid = free_reply["rid"]
                letter = RID_TO_LETTER[rid]
                task = [1, cid, letter]
                print(f"🧪 Scheduling new experiment task: {task}")
                requests.post(ADD_TASK_API, json={"task": task})
            else:
                print("🔴 No free reactors.")
        else:
            print("🔴 No new experiments.")
    except Exception as e:
        print(f"[ERROR] Scheduler error: {e}")


def keep_robot_alive(client):
    while True:
        try:
            res = requests.get(QUEUE_API)
            queue_empty = res.ok and not res.json().get("queue", [])
            if queue_empty and not robot_busy:
                #print("💤 Robot idle — sending keep-alive: attach 1")
                client.SendCommand("attach 1")
        except Exception as e:
            print(f"[WARN] Keep-alive failed: {e}")
        time.sleep(500)  


def main():

    payload = {"task": ""}
    resp = requests.post("http://127.0.0.1:1880/task-update", json=payload, timeout=1)
    time.sleep(0.5)
    payload = {"weight": 0.0}
    res = requests.post("http://127.0.0.1:1880/weight-update", json=payload, timeout=1)

    global robot_busy
    time.sleep(0.5)
    resp = requests.post("http://127.0.0.1:1880/robot-status", json={"status": "busy"}, timeout=1)
    time.sleep(0.5)
    print("⚙️  Initializing robot...")
    client = robot_setup.setup_robot()
    print("✅ Robot ready. Starting task loop.")
    time.sleep(0.5)
    resp = requests.post("http://127.0.0.1:1880/robot-status", json={"status": "idle"}, timeout=1)
    time.sleep(0.5)

    # Start keep-alive thread
    threading.Thread(target=keep_robot_alive, args=(client,), daemon=True).start()

    while True:
        try:
            # If queue is empty, schedule one experiment task
            res = requests.get(QUEUE_API)
            if res.ok:
                queue = res.json().get("queue", [])
                if not queue:
                    #print("📭 Task queue empty — attempting to schedule new experiment...")
                    schedule_new_experiment()
                    time.sleep(5)
                    continue

            # Run task if available
            res = requests.get(TASK_API)
            if res.ok and res.json().get("task"):
                task = res.json()["task"]
                process_task(task, client)
            else:
                print("💤 No task available. Sleeping 10s...")
                time.sleep(10)

        except Exception as e:
            print(f"[ERROR] Main loop error: {e}")
            time.sleep(10)


if __name__ == "__main__":
    main()
