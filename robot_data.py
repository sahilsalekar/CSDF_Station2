# robat_data.py

import time
import datetime

dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def pf3400_rail(client, position_name: str):

    def get_value(command: str):
        """Send command and return only the second part (after '0')."""
        resp = client.SendCommand(command)
        time.sleep(0.5)
        if isinstance(resp, str):
            parts = resp.split(" ", 1)  # split only once
            if len(parts) > 1:
                return parts[1].strip()
        return resp  # fallback if unexpected

    robot_pos = get_value("pd 3504")   # Actual joint angles in deg or mm
    robot_temp = get_value("pd 126 1 0 3")
    robot_time = get_value("pd 3521")
    robot_speed = get_value("pd 601")  # Global speed in %

    robot_data = {
        "Robot Name": "PF3400 SCARA Robot",
        "Robot Serial Number": "FXB-2410-4C-01283(Rail))",
        "Asset ID": "",
        "Robot Location": "TIC 617",
        "Timestamp": dt,
        "Position Name": position_name,
        "Robot Position": robot_pos,
        "Robot Position Type": "Joint Position",
        "Controller Temperature": robot_temp,
        "Speed": robot_speed,
        "Trajectory Time": robot_time
    }
    return robot_data

def pf3400_robot(client, position_name: str):

    def get_value(command: str):
        """Send command and return only the second part (after '0')."""
        resp = client.SendCommand(command)
        time.sleep(0.5)
        if isinstance(resp, str):
            parts = resp.split(" ", 1)  # split only once
            if len(parts) > 1:
                return parts[1].strip()
        return resp  # fallback if unexpected

    robot_pos = get_value("pd 3504")   # Actual joint angles in deg or mm
    robot_temp = get_value("pd 126 1 0 3")
    robot_time = get_value("pd 3521")
    robot_speed = get_value("pd 601")  # Global speed in %

    robot_data = {
        "Robot Name": "PF3400 SCARA Robot",
        "Robot Serial Number": "FXB-2410-4C-01283",
        "Asset ID": "",
        "Robot Location": "TIC 617",
        "Timestamp": dt,
        "Position Name": position_name,
        "Robot Position": robot_pos,
        "Robot Position Type": "Cartesian Position",
        "Controller Temperature": robot_temp,
        "Speed": robot_speed,
        "Trajectory Time": robot_time
    }
    return robot_data