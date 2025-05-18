import subprocess
import time
import os
import sys

SERVICES = [
    ("Task Manager", "task_service.py"),
    ("Status Manager", "status_service.py"),
    ("Tray Monitor", "tray_monitor_service.py"),
]

WORKERS = [
    #("Experiment Scheduler", "experiment_scheduler.py"),
    ("Robot Executor", "robot_executor.py"),
]

def launch_process(name, file):
    print(f"🚀 Starting {name}...")
    return subprocess.Popen([sys.executable, file], stdout=sys.stdout, stderr=sys.stderr)

def main():
    processes = []

    # Start services (FastAPI apps)
    for name, file in SERVICES:
        p = launch_process(name, file)
        processes.append(p)
        time.sleep(1)

    # Start workers (terminal-based background scripts)
    for name, file in WORKERS:
        p = launch_process(name, file)
        processes.append(p)
        time.sleep(1)

    print("\n✅ All services and workers started.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down all processes...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.wait()
        print("✅ All processes stopped cleanly.")

if __name__ == "__main__":
    main()
