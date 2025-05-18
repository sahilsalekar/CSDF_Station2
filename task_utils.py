import json
import os

TASK_FILE = "tasks.json"

def load_tasks():
    if not os.path.exists(TASK_FILE):
        return []
    try:
        with open(TASK_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load tasks: {e}")
        return []

def save_tasks(tasks):
    try:
        with open(TASK_FILE, "w") as f:
            json.dump(tasks, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to save tasks: {e}")

def pop_task():
    tasks = load_tasks()
    if tasks:
        tasks.pop(0)
        save_tasks(tasks)
