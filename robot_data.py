# robot_data.py

import time
import datetime
import requests 

API_URL = "http://130.159.87.150:8000/robot-data"


def _send_to_endpoint(payload: dict):
    """Send robot data dict to the FastAPI endpoint."""
    try:
        response = requests.post(API_URL, json=payload, timeout=5)
        # Optional: raise for HTTP errors
        response.raise_for_status()
        print(f"[robot_data] Sent data OK: {response.status_code}")
        return response
    except requests.RequestException as e:
        # You can log this properly instead of print
        print(f"[robot_data] Failed to send data: {e}")
        return None


def pf3400_rail(client, position_name: str, send: bool = True):
    def get_value(command: str):
        """Send command and return only the second part (after '0')."""
        resp = client.SendCommand(command)
        time.sleep(0.5)
        if isinstance(resp, str):
            parts = resp.split(" ", 1)  # split only once
            if len(parts) > 1:
                return parts[1].strip()
        return resp  # fallback if unexpected

    dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    robot_pos = get_value("pd 3504")   # Actual joint angles in deg or mm
    robot_temp = get_value("pd 126 1 0 3")
    robot_time = get_value("pd 3521")
    robot_speed = get_value("pd 601")  # Global speed in %

    robot_data = {
        "Robot Name": "PF3400 SCARA Robot",
        "Robot Serial Number": "FXB-2410-4C-01283(Rail))",
        "Asset ID": "INV025957",
        "Robot Location": "TIC 617",
        "Timestamp": dt,
        "Position Name": position_name,
        "Robot Position": robot_pos,
        "Robot Position Type": "Joint Position",
        "Controller Temperature": robot_temp,
        "Speed": robot_speed,
        "Trajectory Time": robot_time
    }

    if send:
        _send_to_endpoint(robot_data)

    # Still return the data in case caller wants to log/use it
    return robot_data


def pf3400_robot(client, position_name: str, send: bool = True):
    def get_value(command: str):
        """Send command and return only the second part (after '0')."""
        resp = client.SendCommand(command)
        time.sleep(0.5)
        if isinstance(resp, str):
            parts = resp.split(" ", 1)
            if len(parts) > 1:
                return parts[1].strip()
        return resp

    dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    robot_pos = get_value("pd 3504")
    robot_temp = get_value("pd 126 1 0 3")
    robot_time = get_value("pd 3521")
    robot_speed = get_value("pd 601")

    robot_data = {
        "Robot Name": "PF3400 SCARA Robot",
        "Robot Serial Number": "FXB-2410-4C-01283",
        "Asset ID": "INV025957",
        "Robot Location": "TIC 617",
        "Timestamp": dt,
        "Position Name": position_name,
        "Robot Position": robot_pos,
        "Robot Position Type": "Cartesian Position",
        "Controller Temperature": robot_temp,
        "Speed": robot_speed,
        "Trajectory Time": robot_time
    }

    if send:
        _send_to_endpoint(robot_data)

    return robot_data
