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
            
            client.SendCommand("movec 1 1542.646 67.995 486.104 89.232 90 180 2") # QR Point
            reply = client.SendCommand("waitforeom")
            if reply == "0":
                print("Robot moved to QR point.")

                client.SendCommand("graspplate 117 60 10")
                reply = client.SendCommand("waitforeom")

                client.SendCommand("movec 1 1542.649 67.995 674.255 89.231 90 180 2") # QR APP
                reply = client.SendCommand("waitforeom")

            else:
                print("Robot did not move to QR point.")
                raise RuntimeError("Robot Failed to move to qr point! Stopping Execution.")

            

        else:
            print("Robot did not move to QR.")
            raise RuntimeError("Failed to move to QR! Stopping Execution.")

    except Exception as e:
        print(f"Error in qr_place_vial: {e}")
        raise
