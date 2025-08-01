import time

def qr_place_vial(client):
    """
    Executes Routine_qr_place_vial commands.
    """
    print("Executing Routine qr_place_vial")
    try:
        # Robot to QR
        client.SendCommand("moveoneaxis 6 999.837 1")
        reply = client.SendCommand("waitforeom")
        if reply == "0":
            print("Robot moved to QR.")

            client.SendCommand("movej 1 674.255 11.718 316.242 121.271 109.165 999.837") # QR APP
            reply = client.SendCommand("waitforeom")
            
            client.SendCommand("moveoneaxis 4 -238.744 1")
            reply = client.SendCommand("waitforeom")
        
            command = client.SendCommand("placeplate 8")
            reply = client.SendCommand("waitforeom")
            

        else:
            print("Robot did not move to QR.")
            raise RuntimeError("Failed to move to QR! Stopping Execution.")

    except Exception as e:
        print(f"Error in qr_place_vial: {e}")
        raise
