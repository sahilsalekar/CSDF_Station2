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

            client.SendCommand("movej 1 645.401 12.519 313.734 121.907 109.165 999.837")
            reply = client.SendCommand("waitforeom")
        
            client.SendCommand("graspplate 117 60 10")
            reply = client.SendCommand("waitforeom")
        
            client.SendCommand("movec 1 1540.111 64.784 486.108 88.156 90 180 2")
            reply = client.SendCommand("waitforeom")
            if reply == "0":
                print("Robot moved to QR point.")

                client.SendCommand("graspplate -117 60 10")
                reply = client.SendCommand("waitforeom")

                client.SendCommand("movec 1 1540.123 64.833 645.396 88.161 90 180 2")
                reply = client.SendCommand("waitforeom")

            else:
                print("Robot did not move to QR point.")
                raise RuntimeError("Robot Failed to move to qr point! Stopping Execution.")

            
        else:
            print("Robot did not move to QR.")
            raise RuntimeError("Failed to move to QR! Stopping Execution.")
        
    

    except Exception as e:
        print(f"Error in qr_pick_vial: {e}")