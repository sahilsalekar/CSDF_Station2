import time

def qr_pick_vial(client):
    """
    Executes Routine_qr_pick_vial commands.
    """
    print("Executing Routine qr_pick_vial")
    try:

        # Robot to QR
        client.SendCommand("moveoneaxis 6 999.837 1")
        reply = client.SendCommand("waitforeom")
        if reply == "0":
            print("Robot moved to QR.")

            command = client.SendCommand("pickplate 8")
            reply = client.SendCommand("waitforeom")

            if command == '0 -1':

                client.SendCommand("moveoneaxis 4 121.271 1")
                reply = client.SendCommand("waitforeom")
        
            else:

                client.SendCommand("moveoneaxis 4 121.271 1")
                reply = client.SendCommand("waitforeom")

                client.SendCommand("movej 1 732.082 -2.902 180.537 178.063 109.165 999.837")
                reply = client.SendCommand("waitforeom")

                raise           
            
        else:
            print("Robot did not move to QR.")
            raise RuntimeError("Failed to move to QR! Stopping Execution.")
        
    

    except Exception as e:
        print(f"Error in qr_pick_vial: {e}")