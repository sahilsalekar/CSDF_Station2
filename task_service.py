from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from queue import Queue
import uvicorn
import json
import threading
import os

app = FastAPI()

TASK_FILE = "tasks.json"
task_queue = Queue()
lock = threading.Lock()  # Ensures thread-safe file writes

class Task(BaseModel):
    task: List  # e.g., [1, 5, "A"]

def load_tasks():
    if os.path.exists(TASK_FILE):
        with open(TASK_FILE, "r") as f:
            tasks = json.load(f)
            for task in tasks:
                task_queue.put(task)

def save_tasks():
    with lock:
        with open(TASK_FILE, "w") as f:
            json.dump(list(task_queue.queue), f, indent=2)

@app.on_event("startup")
def startup_event():
    load_tasks()

@app.post("/add_task")
def add_task(task: Task):
    if task.task in list(task_queue.queue):
        return {"status": "Task already exists", "task": task.task}
    task_queue.put(task.task)
    save_tasks()
    return {"status": "Task added", "task": task.task}

@app.get("/next_task")
def get_next_task():
    if not task_queue.empty():
        task = task_queue.get()
        save_tasks()
        return {"task": task}
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

if __name__ == "__main__":
    uvicorn.run("task_service:app", host="0.0.0.0", port=8000, reload=False)
