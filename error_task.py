import json

# Add task to error_task.json
def add_error_task(exp_id, cid, rid):
    error_task_file = "error_task.json"
    try:
        # Load existing data or start fresh
        try:
            with open(error_task_file, "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = []

        # Append new entry
        data.append({"exp_id": exp_id, "cid": cid, "rid": rid})

        # Write back to file
        with open(error_task_file, "w") as f:
            json.dump(data, f, indent=2)

        print(f"[📥] Added to error_task.json: exp_id={exp_id}, cid={cid}, rid={rid}")
    except Exception as e:
        print(f"[ERROR] Failed to write to error_task.json: {e}")