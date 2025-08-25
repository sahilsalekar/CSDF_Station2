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
        
            #client.SendCommand("moveoneaxis 4 -238.744 1")
            #reply = client.SendCommand("waitforeom")
        
            command = client.SendCommand("pickplate 8")
            reply = client.SendCommand("waitforeom")

            if command == '0 0':
                #client.SendCommand("moveoneaxis 4 121.271 1")
                #reply = client.SendCommand("waitforeom")
                print("Vial Not present at QR")
            else:
                #client.SendCommand("moveoneaxis 4 121.271 1")
                #reply = client.SendCommand("waitforeom")

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
