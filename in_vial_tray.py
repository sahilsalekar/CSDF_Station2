import time
import os

def in_vial_tray(client):
    """
    Executes Routine_in_vial_tray commands.
    """
    print("Executing Routine in_vial_tray")
    
    try:
        # Robot to Tray
        client.SendCommand("moveoneaxis 6 840.054 1")
        reply = client.SendCommand("waitforeom")
        if reply == "0":
            print("Robot moved to In Tray.")

            # Safe Pos
            client.SendCommand("moveoneaxis 1 571.951 1")
            reply = client.SendCommand("waitforeom")

            #client.SendCommand("moveoneaxis 4 -361.814 1")
            #reply = client.SendCommand("waitforeom")


            while True:
                # Check if file exists and is not empty
                if not os.path.exists("tray_pos.txt") or os.stat("tray_pos.txt").st_size == 0:
                    raise RuntimeError("Error: tray_pos.txt is empty or missing! Stopping Execution.")

                # Read File
                with open("tray_pos.txt", "r") as file:
                    content = file.read().strip()
                    
                    # Check if content is a valid integer
                    if not content.isdigit():
                        raise RuntimeError("Error: Invalid content in tray_pos.txt! Stopping Execution.")
                    
                    tray_pos = int(content)

                # If tray_pos exceeds 7, exit loop
                if tray_pos > 7:
                    print("Max tray position reached. Exiting loop.")
                    break

                # Determine pallet index based on tray_pos
                pallet_index = [
                    (7, 1, 1), (7, 1, 2), (7, 1, 3), (7, 1, 4),
                    (7, 2, 1), (7, 2, 2), (7, 2, 3), (7, 2, 4)
                ]
                cmd_args = pallet_index[tray_pos]  # Select corresponding index

                # Send pallet index command
                command = f"palletindex {cmd_args[0]} {cmd_args[1]} {cmd_args[2]}"
                client.SendCommand(command)
                reply = client.SendCommand("waitforeom")
                
                # Increment tray position and write to file
                tray_pos += 1
                with open("tray_pos.txt", "w") as file:
                    file.write(str(tray_pos))

                time.sleep(0.5)

                # Try to pick the plate
                reply = client.SendCommand("pickplate 7")
                client.SendCommand("waitforeom")

                if reply == "0 -1":
                    #print("Vial present. Task complete.")
                    # Safe Pos
                    #client.SendCommand("moveoneaxis 4 120.095 1")
                    #reply = client.SendCommand("waitforeom")
                    
                    # Safepos
                    reply = client.SendCommand("movec 1 1012.839 -22.871 571.949 -0.507 90 180 2")
                    client.SendCommand("waitforeom")
                    return True # Vial Found
                else:
                    print("Vial not present. Retrying...")

                    if tray_pos == 8:
                        #client.SendCommand("moveoneaxis 4 120.095 1")
                        #reply = client.SendCommand("waitforeom")

                        # Safepos
                        reply = client.SendCommand("movec 1 1012.839 -22.871 571.949 -0.507 90 180 2")
                        client.SendCommand("waitforeom")
                        return False # No vial found
                        #raise RuntimeError("No Vial Found in - in tray!")

        else:
            #print("Robot did not move to in Tray.")
            raise  

        
    except Exception as e:
        print(f"Error in in_vial_tray: {e}")
        raise
