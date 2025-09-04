# log.py

import os
from pathlib import Path
from datetime import datetime

def write_log(text: str) -> Path:
    """
    Creates folders if they don't exist.
    File name is current datetime (YYYY-MM-DD_HH-MM-SS.log).
    """
    # Get Public Documents path
    public_docs = Path(os.environ.get("PUBLIC", r"C:\Users\Public")) / "Documents"
    
    # Build CSDF/Station_2 path
    log_dir = public_docs / "CSDF" / "Station_2"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Build timestamped log file name
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = log_dir / f"{ts}.log"

    # Write the text
    with log_path.open("w", encoding="utf-8") as f:
        f.write(text.rstrip("\n") + "\n")