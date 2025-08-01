import time
import S71200_PLC
import failvial

def balance_check(client):
    """
    Executes Routine_balance_check commands.
    """
    print("Executing Routine balance_check")
    try:
        # PLC Code
        S71200_PLC.write_memory_bit(100, 0, False) # Open(100.0)
        time.sleep(1)
        S71200_PLC.write_memory_bit(100, 1, False) # Close(100.1)
        time.sleep(1)
    
        S71200_PLC.write_memory_bit(100, 0, True)
        time.sleep(5)
        S71200_PLC.write_memory_bit(100, 0, False)
        time.sleep(1)

        Shield_sensor = S71200_PLC.read_input_bit(0, 0)

        if not Shield_sensor:   

            # Robot to Balance
            client.SendCommand("moveoneaxis 6 343.377 1")
            reply = client.SendCommand("waitforeom")
            if reply == "0":
                print("Robot moved to Balance.")

                client.SendCommand("movej 1 1022.981 -1.398 124.000 179.77 103.064 343.377") # Safe Pos Balance
                reply = client.SendCommand("waitforeom")
                
                client.SendCommand("movej 1 1022.981 -16.638 113.639 -7.258 115.873 343.377") # Balance approach
                reply = client.SendCommand("waitforeom")
            
                command = client.SendCommand("pickplate 9")
                reply = client.SendCommand("waitforeom")

                if command == '0 0':

                    client.SendCommand("movej 1 1022.981 -1.398 124.000 179.77 103.064 343.377") # Safe Pos Balance
                    reply = client.SendCommand("waitforeom")

                    client.SendCommand("movej 1 1022.981 -2.902 180.537 178.063 103.542 343.377") # Safe Pos Balance
                    reply = client.SendCommand("waitforeom")

                else:

                    client.SendCommand("movej 1 1022.981 -1.398 124.000 179.77 109.165 343.377") # Safe Pos Balance
                    reply = client.SendCommand("waitforeom")

                    client.SendCommand("movej 1 1022.981 -2.902 180.537 178.063 109.165 343.377") # Safe Pos Balance
                    reply = client.SendCommand("waitforeom")

                    print("Vial present")

                    failvial.failvial(client)
                    return
                    #raise RuntimeError("Vial Present at Balance! Stopping Execution")

            else:
                print("Robot did not move to Balance.")
                raise RuntimeError("Robot failed to move to Balance! Stopping Execution.")
            
    except Exception as e:
        print(f"Error in balance_check: {e}")
        raise

    finally:
        S71200_PLC.write_memory_bit(100, 1, True)
        time.sleep(5)
        S71200_PLC.write_memory_bit(100, 1, False)
        time.sleep(1)
