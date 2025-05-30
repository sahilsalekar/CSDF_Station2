import time
import failvial

def qr_check(client):
    """
    Executes Routine_qr_check commands.
    """
    print("Executing Routine qr_check")
    try:
        # Robot to QR
        client.SendCommand("moveoneaxis 6 999.837 1")
        reply = client.SendCommand("waitforeom")
        if reply == "0":
            print("Robot moved to qr.")
            client.SendCommand("movej 1 674.255 11.718 316.242 121.271 109.165 999.837")
            reply = client.SendCommand("waitforeom")
        
            client.SendCommand("graspplate 117 60 10")
            reply = client.SendCommand("waitforeom")
        
            client.SendCommand("movec 1 1542.646 67.995 486.104 89.232 90 180 2")
            reply = client.SendCommand("waitforeom")
            if reply == "0":
                print("Robot moved to QR point.")
            else:
                print("Robot did not move to QR point.")
                raise RuntimeError("Robot Failed to move to qr point! Stopping Execution.")

            command = client.SendCommand("graspplate -117 60 10")
            reply = client.SendCommand("waitforeom")

            if command == '0 0':
                client.SendCommand("movec 1 1542.649 67.995 674.255 89.231 90 180 2")
                reply = client.SendCommand("waitforeom")
            else:
                client.SendCommand("movej 1 732.082 13.885 309.756 122.314 109.165 999.837")
                reply = client.SendCommand("waitforeom")

                client.SendCommand("movej 1 732.082 -2.902 180.537 178.063 109.165 999.837")
                reply = client.SendCommand("waitforeom")

                print("Vial present")
                failvial.failvial(client)
                raise
                #raise RuntimeError("Vial Present at QR! Stopping Execution")

        else:
            print("Robot did not move to qr.")
            raise RuntimeError("Robot failed to move to qr! Stopping Execution.")
        
    except Exception as e:
        print(f"Error in qr_check: {e}")
        raise
