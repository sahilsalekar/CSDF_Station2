import time
import qr_check
import qr_place_vial
import qr_pick_vial
import in_vial_tray
import failvial
from plc_qr_seq import plc_qr_seq
from dashboard import Dashboard
import json
import balance_check
import balance_pick
import balance_place
from balance_tcp import BalanceTCPClient

dash = Dashboard()

sta_num = 1
axis_6 = -935.664

# Helper function for qr retry
def read_qr_with_retry(max_tries=2, delay=0.5):
    """
    Try reading QR up to `max_tries` times. 
    Returns the final qr_data dict from plc_qr_seq().
    """
    last = None
    for attempt in range(1, max_tries + 1):
        qr_data = plc_qr_seq()
        if qr_data.get("success"):
            return qr_data
        print(f"[WARN] QR scan failed (attempt {attempt}/{max_tries}). "
              f"Error: {qr_data.get('error') or qr_data.get('data')}")
        last = qr_data
        if attempt < max_tries:
            time.sleep(delay)
    return last or {"success": False, "error": "Unknown QR error"}

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
    print(f"Running 1Station1 with palletindex {sta_num} {pallet_row} {pallet_col}")

    cid = sta_num
    rid = (pallet_row - 1) * 4 + (pallet_col - 1)
    
    try:
        
        client.SendCommand(f"palletindex {sta_num} {pallet_row} {pallet_col}")
        reply = client.SendCommand("waitforeom")
        if reply == "0":
            print(f"Pallet index set successfully to {sta_num} {pallet_row} {pallet_col}")

            # Move to Crystalline 1
            client.SendCommand(f"moveoneaxis 6 {axis_6} 1")
            reply = client.SendCommand("waitforeom")

            if reply == "0":
                # Below Row
                client.SendCommand("moveoneaxis 1 319.49 1")
                reply = client.SendCommand("waitforeom")

                # safe postion (check axis 6)
                client.SendCommand(f"movej 1 319.49 -1.398 124.000 179.77 103.064 {axis_6}")
                reply = client.SendCommand("waitforeom") 

                time.sleep(0.5)

                reply = client.SendCommand(f"pickplate {sta_num}")
                client.SendCommand("waitforeom")

                if reply == "0 0":
                    print("Vial not present")

                    client.SendCommand(f"movej 2 319.49 -1.398 124.000 179.77 103.064 {axis_6}")
                    reply = client.SendCommand("waitforeom")

                    client.SendCommand(f"movej 2 319.49 -2.902 180.537 178.063 103.542 {axis_6}")
                    reply = client.SendCommand("waitforeom")

                    client.SendCommand("moveoneaxis 1 1017.83 1")
                    reply = client.SendCommand("waitforeom")

                    # Balance Check
                    balance_check.balance_check(client)

                    time.sleep(0.5)

                    # QR Check
                    print("Executing qr_check")
                    qr_check.qr_check(client)

                    time.sleep(0.5)

                    # in vial tray
                    print("Exeuting in_vial_tray")
                    if not in_vial_tray.in_vial_tray(client):
                        return

                    time.sleep(0.5)

                    # Qr place vial
                    print("Executing qr_place_vial")
                    qr_place_vial.qr_place_vial(client)

                    # qr plc sequence
                    print("Executing qr plc sequence")
                    qr_data = read_qr_with_retry(max_tries=2, delay=0.5)

                    if qr_data.get("success"):
                        print(f"Scan Okay: {qr_data['data']}")
                        vial_id = qr_data['data']
                        exp_response = dash.get_experiment_id(vial_id)

                        if exp_response and exp_response.get("found"):
                            exp_id = exp_response["exp_id"]
                            print(f"Experiment found for vial {vial_id}: exp_id = {exp_id}")

                            # qr pick vial
                            print("Executing qr_pick_vial")
                            qr_pick_vial.qr_pick_vial(client)
                            time.sleep(0.5)

                        else:
                            exp_id = None
                            print(f"No experiment found for vial {vial_id}.")

                            # qr pick vial
                            print("Executing qr_pick_vial")
                            qr_pick_vial.qr_pick_vial(client)
                            time.sleep(0.5)

                            # fail vial
                            print("Executing fail vial")
                            failvial.failvial(client)
                            return
                                           
                        # balance place
                        balance_place.balance_place(client)

                        time.sleep(0.5)

                        # balance weigh
                        balance = BalanceTCPClient()
                        result = balance.read_weight()
                        balance.disconnect()

                        time.sleep(0.5)

                        if result["success"]:
                            weight_mg = result["data"]
                            # send weight
                            resp = dash.add_vial_mass(named_time="START", mass=weight_mg, exp_id=exp_id)

                            time.sleep(0.5)

                            # balance pick
                            balance_pick.balance_pick(client)

                        else:
                            print("Retrying weight read...")
                            # balance weigh
                            balance = BalanceTCPClient()
                            result = balance.read_weight()
                            balance.disconnect()

                            if result["success"]:
                                weight_mg = result["data"]
                                # send weight
                                resp = dash.add_vial_mass(named_time="START", mass=weight_mg, exp_id=exp_id)

                                time.sleep(0.5)

                                # balance pick
                                balance_pick.balance_pick(client)

                            else:
                                print("Error Reading weight")

                                # balance pick
                                balance_pick.balance_pick(client)

                                time.sleep(0.5)

                                # fail vial
                                print("Executing fail vial")
                                failvial.failvial(client)
                                return

                        
                        time.sleep(0.5)
                        
                        client.SendCommand(f"moveoneaxis 6 {axis_6} 1")
                        reply = client.SendCommand("waitforeom")

                        # Below Row
                        client.SendCommand("moveoneaxis 1 319.49 1")
                        reply = client.SendCommand("waitforeom")

                        # safe postion
                        client.SendCommand(f"movej 2 319.49 -1.398 124.000 179.77 103.064 {axis_6}")
                        reply = client.SendCommand("waitforeom") 

                        client.SendCommand(f"movej 2 319.49 -1.398 124 -0.849 103.081 {axis_6}")
                        reply = client.SendCommand("waitforeom")

                        time.sleep(0.5)

                        client.SendCommand(f"placeplate {sta_num}")
                        reply = client.SendCommand("waitforeom")

                        # Push Move
                        # close gripper
                        client.SendCommand("graspplate -119 60 10")
                        reply = client.SendCommand("waitforeom")

                        client.SendCommand("moveoneaxis 1 183.678 1")
                        reply = client.SendCommand("waitforeom")

                        client.SendCommand("moveoneaxis 1 195 1")
                        reply = client.SendCommand("waitforeom")

                        time.sleep(5)

                        # Check vial present before starting exp
                        # open gripper
                        command = client.SendCommand("graspplate 117 60 10")
                        #reply = client.SendCommand("waitforeom")
                        if command == "0 0":
                            command = client.SendCommand("moveoneaxis 1 172.411 2")
                            reply = client.SendCommand("waitforeom")
                            if command == "0":
                                command = client.SendCommand("graspplate -117 60 10")
                                #reply = client.SendCommand("waitforeom")
                                if command == "0 -1":
                                    print("Vial Present Starting Experiment")
                                    # open gripper
                                    client.SendCommand("graspplate 117 60 10")
                                    reply = client.SendCommand("waitforeom")

                                    client.SendCommand("moveoneaxis 1 307.79 1")
                                    reply = client.SendCommand("waitforeom")

                                else:
                                    print("Vial Not Present Stopping Execution")
                                    # open gripper
                                    client.SendCommand("graspplate 117 60 10")
                                    reply = client.SendCommand("waitforeom")

                                    client.SendCommand("moveoneaxis 1 307.79 1")
                                    reply = client.SendCommand("waitforeom")

                                    # safe postion
                                    client.SendCommand(f"movej 2 319.49 -1.398 124.000 179.77 103.064 {axis_6}")
                                    reply = client.SendCommand("waitforeom")

                                    client.SendCommand(f"movej 2 319.49 -1.398 184.317 179.77 103.064 {axis_6}")
                                    reply = client.SendCommand("waitforeom")
                                    return
                            else:
                                print("Robot Didn't Reach Vial Point. Stoping Execution")
                                client.SendCommand("moveoneaxis 1 307.79 1")
                                reply = client.SendCommand("waitforeom")

                                # safe postion
                                client.SendCommand(f"movej 2 319.49 -1.398 124.000 179.77 103.064 {axis_6}")
                                reply = client.SendCommand("waitforeom")

                                client.SendCommand(f"movej 2 319.49 -1.398 184.317 179.77 103.064 {axis_6}")
                                reply = client.SendCommand("waitforeom")
                                return
                        else:
                            print("Gripper Didn't Open. Stopping Execution")

                            client.SendCommand("moveoneaxis 1 307.79 1")
                            reply = client.SendCommand("waitforeom")

                            # safe postion
                            client.SendCommand(f"movej 2 319.49 -1.398 124.000 179.77 103.064 {axis_6}")
                            reply = client.SendCommand("waitforeom")

                            client.SendCommand(f"movej 2 319.49 -1.398 184.317 179.77 103.064 {axis_6}")
                            reply = client.SendCommand("waitforeom")
                            return

                        # safe postion
                        client.SendCommand(f"movej 2 319.49 -1.398 124.000 179.77 103.064 {axis_6}")
                        reply = client.SendCommand("waitforeom")

                        client.SendCommand(f"movej 2 319.49 -1.398 184.317 179.77 103.064 {axis_6}")
                        reply = client.SendCommand("waitforeom")

                        #Home position
                        client.SendCommand("movej 1 1017.83 -2.902 180.537 178.063 103.542 -934.686")
                        reply = client.SendCommand("waitforeom")

                        #Intiate Experiment
                        max_retries = 3
                        for attempt in range(1, max_retries + 1):
                            try:
                                dash.initiate_experiment(exp_id, cid, rid)
                                print(f"✅ Experiment started at {cid} {rid} with experiment id {exp_id}")
                                break  # success, exit retry loop
                            except Exception as e:
                                print(f"[WARN] Attempt {attempt}: Failed to initiate experiment (exp_id={exp_id}) — {e}")
                                if attempt < max_retries:
                                    print("⏳ Retrying in 5 seconds...")
                                    time.sleep(5)
                                else:
                                    print("❌ All retries failed — stopping execution.")
                                    return

                        #append status
                        append_status(exp_id, cid, rid)

                        time.sleep(0.5)

                        print(f"Crystalline {sta_num} {cid} {rid} Complete")
                        time.sleep(5)

                    else:
                        print(f"Scan Failed: {qr_data.get('data')}, Error: {qr_data.get('error')}")
                        qr_pick_vial.qr_pick_vial(client)
                        time.sleep(0.5)
                        failvial.failvial(client)
                        return


                else:
                    client.SendCommand(f"movej 2 319.49 -1.398 124.000 179.77 103.064 {axis_6}")
                    reply = client.SendCommand("waitforeom")

                    client.SendCommand(f"movej 2 319.49 -2.902 180.537 178.063 103.542 {axis_6}")
                    reply = client.SendCommand("waitforeom")

                    failvial.failvial(client)
                    time.sleep(0.5)

                    #raise RuntimeError(f"Vial Present at {sta_num} {pallet_row} {pallet_col}! Stopping Execution")
                    return

            else:
                print(f"Failed to move to Crystalline {sta_num}! Stopping Execution")
                #raise RuntimeError(f"Failed to move to Crystalline {sta_num}! Stopping Execution")
                return

        else:
            print(f"Failed to set pallet index {sta_num} {cid} {rid}! Stopping Execution")
            #raise RuntimeError(f"Failed to set pallet index {sta_num} {pallet_row} {pallet_col}! Stopping Execution")
            return

    except Exception as e:
        print(f'[ERROR] In {sta_num} {cid} {rid} {e}')
        raise
    
    finally:
        #Home position
        client.SendCommand("movej 1 1017.83 -2.902 180.537 178.063 103.542 -934.686")
        reply = client.SendCommand("waitforeom")
