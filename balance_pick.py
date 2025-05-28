import time
import S71200_PLC
from balance_tcp import BalanceTCPClient

def balance_pick(client):
    """
    Executes Routine_balance_pick commands.
    """
    print("Executing Routine balance_pick")
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
                client.SendCommand("movej 1 1022.981 -16.638 113.639 -7.258 109.165 343.38") # Balance approach
                reply = client.SendCommand("waitforeom")

                client.SendCommand("graspplate 117 60 10")
                reply = client.SendCommand("waitforeom")

                client.SendCommand("movec 1 598.235 360.373 844.706 89.743 90 180 1") # Balance point
                reply = client.SendCommand("waitforeom")
                if reply == "0":
                    print("Robot moved to Balance point.")
                else:
                    print("Robot did not move to Balance point.")
                    raise RuntimeError("Robot Failed to move to balance point! Stopping Execution.")

                client.SendCommand("graspplate -117 60 10")
                reply = client.SendCommand("waitforeom")

                client.SendCommand("movej 1 1022.981 -16.638 113.639 -7.258 109.165 343.38") # Balance approach
                reply = client.SendCommand("waitforeom")

                client.SendCommand("movej 1 1022.981 -1.398 124.000 179.77 109.165 343.38") # Safe Pos Balance
                reply = client.SendCommand("waitforeom")

                client.SendCommand("movej 1 1022.981 -2.902 180.537 178.063 109.165 343.38") # Safe Pos Balance
                reply = client.SendCommand("waitforeom")

                

            else:
                print("Robot did not move to Balance.")
                raise RuntimeError("Robot failed to move to Balance! Stopping Execution.")
            
    except Exception as e:
        print(f"Error in balance_pick: {e}")
        raise

    
