import time
import Vial_to_ventionplace 
from dashboard import Dashboard

dash = Dashboard()

sta_num = 6
axis_6 = 935.165

def run(client, pallet_row, pallet_col):
    print(f"Running 2Station1 with palletindex {sta_num} {pallet_row} {pallet_col}")
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
                    
                    # mark reactor free
                    dash.mark_reactor_free(cid, letter)
                    print(f"Reactor {cid} {letter} marked free")

                    print(f"Crystalline {sta_num} {pallet_row} {pallet_col} Complete")    

                else:
                    client.SendCommand(f"movej 1 1021.847 -1.398 124.000 179.77 103.064 {axis_6}")
                    reply = client.SendCommand("waitforeom")

                    client.SendCommand(f"movej 1 1017.83 -2.902 180.537 178.063 103.542 {axis_6}")
                    reply = client.SendCommand("waitforeom")

                    # Home position
                    client.SendCommand("movej 1 1017.83 -2.902 180.537 178.063 103.542 -934.686")
                    reply = client.SendCommand("waitforeom")

                    raise RuntimeError(
                        f"Vial Not Present at {sta_num} {pallet_row} {pallet_col}! Stopping Execution"
                    )

            else:
                print(f"Failed to move to Crystalline {sta_num}! Stopping Execution")
                raise RuntimeError(f"Failed to move to Crystalline {sta_num}! Stopping Execution")

        else:
            print(f"Failed to set pallet index {sta_num} {pallet_row} {pallet_col}! Stopping Execution")
            raise RuntimeError(f"Failed to set pallet index {sta_num} {pallet_row} {pallet_col}! Stopping Execution")

    except Exception as e:
        print(f"[ERROR] In {sta_num} {pallet_row} {pallet_col} {e}")
