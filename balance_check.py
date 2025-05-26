import time
import S71200_PLC

def balance_check(client):
    """
    Executes Routine_balance_check commands.
    """
    print("Executing Routine balance_check")
    try:
        # PLC Code
        S71200_PLC.write_memory_bit(100, 0, False)
        time.sleep(1)
        S71200_PLC.write_memory_bit(100, 1, False)
        time.sleep(1)
        Shield_sensor = S71200_PLC.read_input_bit(0, 0)
        if Shield_sensor:
            S71200_PLC.write_memory_bit(100, 0, True)
            time.sleep(10)

        else:
            S71200_PLC.write_memory_bit(100, 0, True)
            time.sleep(10)

        # Robot to Balance
        client.SendCommand("moveoneaxis 6 999.837 1")
        reply = client.SendCommand("waitforeom")
        if reply == "0":
            print("Robot moved to Balance.")
            client.SendCommand("movej 1 645.401 12.519 313.734 121.907 109.165 999.837")
            reply = client.SendCommand("waitforeom")
        
            client.SendCommand("graspplate 117 60 10")
            reply = client.SendCommand("waitforeom")
        
            client.SendCommand("movec 1 1540.111 64.784 486.108 88.156 90 180 2")
            reply = client.SendCommand("waitforeom")
            if reply == "0":
                print("Robot moved to QR point.")
            else:
                print("Robot did not move to QR point.")
                raise RuntimeError("Robot Failed to move to qr point! Stopping Execution.")

            command = client.SendCommand("graspplate -117 60 10")
            reply = client.SendCommand("waitforeom")

            if command == '0 0':
                client.SendCommand("movec 1 1540.123 64.833 645.396 88.161 90 180 2")
                reply = client.SendCommand("waitforeom")
            else:
                client.SendCommand("movej 1 732.082 13.885 309.756 122.314 115.926 999.837")
                reply = client.SendCommand("waitforeom")

                # Home Pos
                client.SendCommand("movej 1 645.401 12.519 313.734 121.907 109.165 999.837")
                reply = client.SendCommand("waitforeom")

                print("Vial present")
                raise RuntimeError("Vial Present at QR! Stopping Execution")

        else:
            print("Robot did not move to qr.")
            raise RuntimeError("Robot failed to move to qr! Stopping Execution.")
        
    except Exception as e:
        print(f"Error in qr_check: {e}")
        raise