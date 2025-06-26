import time
import S71200_PLC
from balance_tcp import BalanceTCPClient

def balance_place(client):
    """
    Executes Routine_balance_place commands.
    """
    print("Executing Routine balance_place")
    try:
        # PLC Code
        S71200_PLC.write_memory_bit(100, 0, False) # Open(100.0)
        time.sleep(1)
        S71200_PLC.write_memory_bit(100, 1, False) # Close(100.1)
        time.sleep(1)
    
        S71200_PLC.write_memory_bit(100, 1, True)
        time.sleep(5)
        S71200_PLC.write_memory_bit(100, 1, False)
        time.sleep(1)

        Shield_sensor = S71200_PLC.read_input_bit(0, 0)

        if Shield_sensor:   
            
            # Balance Zero
            balance = BalanceTCPClient()
            time.sleep(1)
            zero = balance.zero_balance()
            if zero == "Z A":

                balance.disconnect()
            
            # Robot to Balance
            client.SendCommand("moveoneaxis 6 343.377 1")
            reply = client.SendCommand("waitforeom")
            if reply == "0":
                print("Robot moved to Balance.")

                client.SendCommand("movej 1 1022.981 -1.398 124.000 179.77 103.064 343.38") # Safe Pos Balance
                reply = client.SendCommand("waitforeom")
                
                client.SendCommand("movej 1 1022.981 -16.638 113.639 -7.258 109.165 343.38") # Balance approach
                reply = client.SendCommand("waitforeom")

                # PLC code to open Balance Shield
                S71200_PLC.write_memory_bit(100, 0, True)
                time.sleep(5)
                S71200_PLC.write_memory_bit(100, 0, False)
                time.sleep(1)
                Shield_sensor = S71200_PLC.read_input_bit(0, 0)

                if not Shield_sensor:


                    client.SendCommand("movec 1 598.235 360.373 850.0 89.743 90 180 1") # Balance point
                    reply = client.SendCommand("waitforeom")
                    if reply == "0":
                        print("Robot moved to Balance point.")
                    else:
                        print("Robot did not move to Balance point.")
                        raise RuntimeError("Robot Failed to move to balance point! Stopping Execution.")

                    command = client.SendCommand("graspplate 117 60 10")
                    reply = client.SendCommand("waitforeom")

                    
                    client.SendCommand("movej 1 1022.981 -16.638 113.639 -7.258 115.873 343.38")
                    reply = client.SendCommand("waitforeom")

                    # client.SendCommand("movej 1 1022.981 -1.398 124.000 179.77 103.064 343.38") # Safe Pos Balance
                    # reply = client.SendCommand("waitforeom")

                    # client.SendCommand("movej 1 1022.981 -2.902 180.537 178.063 103.542 343.38") # Safe Pos Balance
                    # reply = client.SendCommand("waitforeom")

                

            else:
                print("Robot did not move to Balance.")
                raise RuntimeError("Robot failed to move to Balance! Stopping Execution.")
            
    except Exception as e:
        print(f"Error in balance_place: {e}")
        raise

    finally:
        S71200_PLC.write_memory_bit(100, 1, True)
        time.sleep(5)
        S71200_PLC.write_memory_bit(100, 1, False)
        time.sleep(1)
