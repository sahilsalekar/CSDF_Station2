#in_vial.py

import time

def in_vial(client):
    """
    Executes Routine in_vial commands.
    """
    print("Executing Routine in_vial")
    
    try:
        # Robot to vial
        client.SendCommand("moveoneaxis 6 816.542 1")
        reply = client.SendCommand("waitforeom")
        if reply == "0":
            print("Robot moved to In Tray.")

            time.sleep(0.5)

            # Try to pick the plate
            reply = client.SendCommand("pickplate 10")
            client.SendCommand("waitforeom")

            if reply == "0 -1":
                
                # Safepos
                reply = client.SendCommand("movec 1 88.67 -37.652 753.486 -4.489 90 180 2")
                client.SendCommand("waitforeom")
                return True # Vial Found
            else:
                print("Vial not present.")
                return False # Vial Not Found

        else:
            #print("Robot did not move to in Tray.")
            raise  

        
    except Exception as e:
        print(f"Error in in_vial: {e}")
        raise
