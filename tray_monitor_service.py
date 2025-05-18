from fastapi import FastAPI, Request
from pydantic import BaseModel
import os
import json

app = FastAPI()
TRAY_FILE = "tray_pos.txt"
MAX_POS = 8

class ResetRequest(BaseModel):
    reset_to: int  # usually 0


def read_tray_pos():
    try:
        if not os.path.exists(TRAY_FILE):
            return 0
        with open(TRAY_FILE, "r") as f:
            content = f.read().strip()
            return int(content) if content.isdigit() else 0
    except Exception as e:
        print(f"[ERROR] Reading tray_pos.txt: {e}")
        return 0


def write_tray_pos(value: int):
    try:
        with open(TRAY_FILE, "w") as f:
            f.write(str(value))
    except Exception as e:
        print(f"[ERROR] Writing tray_pos.txt: {e}")


@app.get("/is_tray_ready")
def is_tray_ready():
    pos = read_tray_pos()
    return {"ready": pos < MAX_POS, "current_pos": pos}


@app.get("/tray_pos")
def get_tray_pos():
    return {"tray_pos": read_tray_pos()}


@app.post("/reset_tray")
def reset_tray(req: ResetRequest):
    write_tray_pos(req.reset_to)
    return {"status": f"Tray position reset to {req.reset_to}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("tray_monitor_service:app", host="0.0.0.0", port=8002, reload=False)
