# 2Station5.py

import time
from qr import qr_check
from qr import qr_place_vial
from qr import qr_pick_vial
import failvial
from plc_qr_seq import plc_qr_seq
from dashboard import Dashboard
from balance import balance_check
from balance import balance_pick
from balance import balance_place
from balance.balance_tcp import BalanceTCPClient
import Vial_to_ventionplace
import requests

dash = Dashboard()

sta_num = 5
axis_6 = -8.886

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

def run(client, pallet_row, pallet_col, exp_id_from_task=None):
    print(f"Running 2Station1 with palletindex {sta_num} {pallet_row} {pallet_col}")
    try:

        # Balance Check
        balance_check.balance_check(client)

        time.sleep(0.5)

        # QR Check
        print("Executing qr_check")
        qr_check.qr_check(client)

        time.sleep(0.5)

        cid = sta_num
        rid = (pallet_row - 1) * 4 + (pallet_col - 1)

        # exp_id passed from tasks.json (authoritative for type-2)
        exp_id_task = exp_id_from_task
        exp_id = exp_id_task  # default effective exp_id

        client.SendCommand(f"palletindex {sta_num} {pallet_row} {pallet_col}")
        reply = client.SendCommand("waitforeom")
        if reply == "0":
            print(f"Pallet index set successfully to {sta_num} {pallet_row} {pallet_col}")

            # Move to Crystalline 5
            client.SendCommand(f"moveoneaxis 6 {axis_6} 1")
            reply = client.SendCommand("waitforeom")

            if reply == "0":
                # safe position (check axis 6)
                client.SendCommand(f"movej 1 1021.847 -1.398 124.000 179.77 103.064 {axis_6}")
                reply = client.SendCommand("waitforeom") 

                time.sleep(0.5)

                reply = client.SendCommand(f"pickplate {sta_num}")
                client.SendCommand("waitforeom")

                if reply == "0 -1":
                    print("Vial present")

                    client.SendCommand(f"movej 2 1021.847 -1.398 124.000 179.77 103.064 {axis_6}")
                    reply = client.SendCommand("waitforeom")

                    client.SendCommand(f"movej 2 1017.83 -2.902 180.537 178.063 103.542 {axis_6}")
                    reply = client.SendCommand("waitforeom")
                    
                    # Check vial in grippers
                    command = client.SendCommand("graspplate -117 60 10")
                    if command != "0 -1":

                        print("Stopping Execution! Vial is not in gripper")
                        # add to error_task
                        import error_task

                        exp_for_error = exp_id_task if exp_id_task is not None else "unknown"
                        error_task.add_error_task(exp_id=exp_for_error, cid=cid, rid=rid)

                        return
                    
                    # convert rid to letter
                    RID_TO_LETTER = "ABCDEFGH"
                    letter = RID_TO_LETTER[rid]

                    # mark reactor free
                    dash.mark_reactor_free(cid, letter)
                    print(f"Reactor {cid} {letter} marked free")

                    # Qr place vial
                    print("Executing qr_place_vial")
                    qr_place_vial.qr_place_vial(client)

                    # qr plc sequence
                    print("Executing qr plc sequence")
                    qr_data = read_qr_with_retry(max_tries=2, delay=0.5)

                    exp_id_from_qr = None

                    if qr_data.get("success"):
                        print(f"Scan Okay: {qr_data['data']}")
                        vial_id = qr_data['data']

                        exp_response = dash.get_experiment_id(vial_id)
                        if exp_response and exp_response.get("found"):
                            exp = exp_response.get("exp") or {}
                            exp_id_from_qr = exp.get("exp_id")
                            print(f"Experiment found for vial {vial_id}: exp_id = {exp_id_from_qr}")
                        else:
                            print(f"No experiment found for vial {vial_id}. exp_id_from_qr=None")
                    else:
                        print(f"Scan Failed: {qr_data.get('data')}, Error: {qr_data.get('error')}")
                        exp_id_from_qr = None


                    # ---- Decide effective exp_id ----
                    # Priority in type-2:
                    # 1) If QR yields exp_id and task exp_id exists -> MUST MATCH, else stop (safety)
                    # 2) If QR yields exp_id and task missing -> use QR exp_id
                    # 3) If QR fails -> use task exp_id (fallback) and continue (NO failvial)

                    if exp_id_from_qr is not None and exp_id_task is not None:
                        if str(exp_id_from_qr).strip() != str(exp_id_task).strip():
                            print(f"[ERROR] EXP_ID MISMATCH! qr={exp_id_from_qr} task={exp_id_task}. Stopping and failing vial.")
                            try:
                                dash.add_note(
                                    exp_id=exp_id_task,
                                    additional_note=f"CSDF Station2 Type-2: EXP_ID mismatch. QR/Dashboard={exp_id_from_qr} but task exp_id={exp_id_task}. Manual intervention required."
                                )
                            except Exception as e:
                                print(f"[WARN] Could not add dashboard note: {e}")

                            # qr pick vial
                            print("Executing qr_pick_vial")
                            qr_pick_vial.qr_pick_vial(client)
                            time.sleep(0.5)

                            # fail vial (mismatch is dangerous)
                            print("Executing fail vial")
                            failvial.failvial(client)
                            return

                        exp_id = exp_id_task  # matched; use task (or QR, same anyway)

                    elif exp_id_from_qr is not None:
                        exp_id = exp_id_from_qr

                    else:
                        # QR failed (or dashboard lookup failed). For type-2, fallback to task exp_id.
                        exp_id = exp_id_task
                        print(f"[WARN] QR scan/lookup failed. Falling back to exp_id from task: {exp_id}")

                        try:
                            dash.add_note(
                                exp_id=exp_id,
                                additional_note=(
                                    "CSDF Station2 Type-2: QR scan failed (after retries). Using exp_id from task JSON. "
                                    "Downstream actions (mass, station3 offline image, Raman) may be associated to fallback exp_id. "
                                    "Please verify vial identity / data association."
                                )
                            )
                        except Exception as e:
                            print(f"[WARN] Could not add dashboard note: {e}")

                        


                    # qr pick vial 
                    print("Executing qr_pick_vial")
                    qr_pick_vial.qr_pick_vial(client)
                    time.sleep(0.5)

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
                        resp = dash.add_vial_mass(named_time="END", mass=weight_mg, exp_id=exp_id)

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
                            resp = dash.add_vial_mass(named_time="END", mass=weight_mg, exp_id=exp_id)

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

                    # Vention Table
                    print("Executing Vention Place")
                    Vial_to_ventionplace.Vial_to_ventionplace(client)
                    print("Successfully completed vention vial place")

                    # Home position
                    client.SendCommand("movej 1 1017.83 -2.902 180.537 178.063 103.542 -934.686")
                    reply = client.SendCommand("waitforeom")

                    response = requests.post("http://localhost:8005/initiate_CSDF_Station3", json={"exp_id": str(exp_id)})

                    print(f"Crystalline {sta_num} {pallet_row} {pallet_col} Complete")    

                else:
                    client.SendCommand(f"movej 1 1021.847 -1.398 124.000 179.77 103.064 {axis_6}")
                    reply = client.SendCommand("waitforeom")

                    client.SendCommand(f"movej 1 1017.83 -2.902 180.537 178.063 103.542 {axis_6}")
                    reply = client.SendCommand("waitforeom")

                    # Home position
                    client.SendCommand("movej 1 1017.83 -2.902 180.537 178.063 103.542 -934.686")
                    reply = client.SendCommand("waitforeom")

                    #raise RuntimeError(f"Vial Not Present at {sta_num} {pallet_row} {pallet_col}! Stopping Execution")
                    return

            else:
                print(f"Failed to move to Crystalline {sta_num}! Stopping Execution")
                #raise RuntimeError(f"Failed to move to Crystalline {sta_num}! Stopping Execution")
                return

        else:
            print(f"Failed to set pallet index {sta_num} {pallet_row} {pallet_col}! Stopping Execution")
            #raise RuntimeError(f"Failed to set pallet index {sta_num} {pallet_row} {pallet_col}! Stopping Execution")
            return

    except Exception as e:
        print(f"[ERROR] In {sta_num} {pallet_row} {pallet_col} {e}")
        raise

    finally:
        #Home position
        client.SendCommand("movej 1 1017.83 -2.902 180.537 178.063 103.542 -934.686")
        reply = client.SendCommand("waitforeom")
