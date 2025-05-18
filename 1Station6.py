import time
import qr_check
import qr_place_vial
import qr_pick_vial
import in_vial_tray
import failvial
from plc_qr_seq import plc_qr_seq
from dashboard import Dashboard
import json

dash = Dashboard()

sta_num = 6
axis_6 = 935.165



# Add task to status.json
def append_status(exp_id, cid, rid):
    status_file = "status.json"
    try:
        # Load existing data or start fresh
        try:
            with open(status_file, "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = []

        # Append new entry
        data.append({"exp_id": exp_id, "cid": cid, "rid": rid})

        # Write back to file
        with open(status_file, "w") as f:
            json.dump(data, f, indent=2)

        print(f"[📥] Added to status.json: exp_id={exp_id}, cid={cid}, rid={rid}")
    except Exception as e:
        print(f"[ERROR] Failed to write to status.json: {e}")

def run(client, pallet_row, pallet_col):
    print(f"Running 1Station6 with palletindex {sta_num} {pallet_row} {pallet_col}")

    try:

        cid = sta_num
        rid = (pallet_row - 1) * 4 + (pallet_col - 1)
        
        client.SendCommand(f"palletindex {sta_num} {pallet_row} {pallet_col}")
        reply = client.SendCommand("waitforeom")
        if reply == "0":
            print(f"Pallet index set successfully to {sta_num} {pallet_row} {pallet_col}")

            # Move to Crystalline 6
            client.SendCommand(f"moveoneaxis 6 {axis_6} 1")
            reply = client.SendCommand("waitforeom")

            if reply == "0":

                # safe postion (check axis 6)
                client.SendCommand(f"movej 1 1021.847 -1.398 124.000 179.77 103.064 {axis_6}")
                reply = client.SendCommand("waitforeom") 

                time.sleep(0.5)

                reply = client.SendCommand(f"pickplate {sta_num}")
                client.SendCommand("waitforeom")

                if reply == "0 0":
                    print("Vial not present")

                    client.SendCommand(f"movej 1 1021.847 -1.398 124.000 179.77 103.064 {axis_6}")
                    reply = client.SendCommand("waitforeom")

                    client.SendCommand(f"movej 1 1017.83 -2.902 180.537 178.063 103.542 {axis_6}")
                    reply = client.SendCommand("waitforeom")

                    # QR Check
                    print("Executing qr_check")
                    qr_check.qr_check(client)

                    time.sleep(0.5)

                    # in vial tray
                    print("Exeuting in_vial_tray")
                    in_vial_tray.in_vial_tray(client)

                    time.sleep(0.5)

                    # Qr place vial
                    print("Executing qr_place_vial")
                    qr_place_vial.qr_place_vial(client)

                    # qr plc sequence
                    print("Executing qr plc sequence")
                    qr_data = plc_qr_seq()

                    if qr_data.get("success"):
                        print(f"Scan Okay: {qr_data['data']}")

                        vial_id = qr_data['data']
                        exp_response = dash.get_experiment_id(vial_id)

                        if exp_response and exp_response.get("found"):
                            exp_id = exp_response["exp_id"]  # ✅ Now this holds the actual exp_id number
                            print(f"Experiment found for vial {vial_id}: exp_id = {exp_id}")
                            # ✅ You can now use exp_id later in your code
                            # qr pick vial
                            print("Executing qr_pick_vial")
                            qr_pick_vial.qr_pick_vial(client)
                            time.sleep(0.5)
                            
                        else:
                            exp_id = None  # Or leave it unset
                            print(f"No experiment found for vial {vial_id}.")
                            # qr pick vial
                            print("Executing qr_pick_vial")
                            qr_pick_vial.qr_pick_vial(client)
                            time.sleep(0.5)

                            # fail vial
                            print("Executing fail vial")
                            failvial.failvial(client)
                            return

                        
                        
                        client.SendCommand(f"moveoneaxis 6 {axis_6} 1")
                        reply = client.SendCommand("waitforeom")

                        # safe postion
                        client.SendCommand(f"movej 1 1021.847 -1.398 124.000 179.77 103.064 {axis_6}")
                        reply = client.SendCommand("waitforeom") 

                        client.SendCommand(f"movej 1 1021.852 -1.398 124 -0.849 103.081 {axis_6}")
                        reply = client.SendCommand("waitforeom")

                        time.sleep(0.5)

                        client.SendCommand(f"placeplate {sta_num}")
                        reply = client.SendCommand("waitforeom") 

                        # safe postion
                        client.SendCommand(f"movej 1 1021.847 -1.398 124.000 179.77 103.064 {axis_6}")
                        reply = client.SendCommand("waitforeom")

                        client.SendCommand(f"movej 1 1021.847 -1.398 184.317 179.77 103.064 {axis_6}")
                        reply = client.SendCommand("waitforeom")

                        #Home position
                        client.SendCommand("movej 1 1017.83 -2.902 180.537 178.063 103.542 -934.686")
                        reply = client.SendCommand("waitforeom")

                        #Intiate Experiment
                        dash.initiate_experiment(exp_id, cid, rid)
                        print(f"Experiment started at {cid} {rid} with experiment id {exp_id}")

                        #append status
                        append_status(exp_id, cid, rid)

                        time.sleep(0.5)

                        print(f"Crystalline {sta_num} {pallet_row} {pallet_col} Complete")
                        time.sleep(5)

                    else:
                        print(f"Scan Failed: {qr_data.get('data')}, Error: {qr_data.get('error')}")

                else:
                    client.SendCommand(f"movej 1 1021.847 -1.398 124.000 179.77 103.0644 {axis_6}")
                    reply = client.SendCommand("waitforeom")

                    client.SendCommand(f"movej 1 1017.83 -2.902 180.537 178.063 103.542 {axis_6}")
                    reply = client.SendCommand("waitforeom")

                    raise RuntimeError(f"Vial Present at {sta_num} {pallet_row} {pallet_col}! Stopping Execution")

            else:
                print(f"Failed to move to Crystalline {sta_num}! Stopping Execution")
                raise RuntimeError(f"Failed to move to Crystalline {sta_num}! Stopping Execution")

        else:
            print(f"Failed to set pallet index {sta_num} {pallet_row} {pallet_col}! Stopping Execution")
            raise RuntimeError(f"Failed to set pallet index {sta_num} {pallet_row} {pallet_col}! Stopping Execution")

    except Exception as e:
        print(f'[ERROR] In {sta_num} {pallet_row} {pallet_col} {e}')

    finally:
        #Home position
        client.SendCommand("movej 1 1017.83 -2.902 180.537 178.063 103.542 -934.686")
        reply = client.SendCommand("waitforeom")