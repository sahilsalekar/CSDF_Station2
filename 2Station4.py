import time
import qr_check
import qr_place_vial
import qr_pick_vial
import failvial
from plc_qr_seq import plc_qr_seq
from dashboard import Dashboard
import balance_check
import balance_pick
import balance_place
from balance_tcp import BalanceTCPClient
import Vial_to_ventionplace
import requests

dash = Dashboard() 

sta_num = 4
axis_6 = -948.090

def run(client, pallet_row, pallet_col):
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

        client.SendCommand(f"palletindex {sta_num} {pallet_row} {pallet_col}")
        reply = client.SendCommand("waitforeom")
        if reply == "0":
            print(f"Pallet index set successfully to {sta_num} {pallet_row} {pallet_col}")

            # Move to Crystalline 1
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

                    client.SendCommand(f"movej 1 1021.847 -1.398 124.000 179.77 103.064 {axis_6}")
                    reply = client.SendCommand("waitforeom")

                    client.SendCommand(f"movej 1 1017.83 -2.902 180.537 178.063 103.542 {axis_6}")
                    reply = client.SendCommand("waitforeom")

                    # mark reactor free
                    dash.mark_reactor_free(cid, letter)
                    print(f"Reactor {cid} {letter} marked free")

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
                    
                    else:
                        print(f"Scan Failed: {qr_data.get('data')}, Error: {qr_data.get('error')}")
                        qr_pick_vial.qr_pick_vial(client)
                        time.sleep(0.5)
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

                    # convert rid to letter
                    RID_TO_LETTER = "ABCDEFGH"
                    letter = RID_TO_LETTER[rid]
                    

                    response = requests.post("http://localhost:8005/initiate_CSDF_Station3")

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
