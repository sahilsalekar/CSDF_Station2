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

                client.SendCommand("movej 1 1046.97 -1.398 124.000 179.77 109.165 343.377") # Safe Pos Balance
                reply = client.SendCommand("waitforeom")
                
                client.SendCommand("movej 1 1046.97 -16.638 113.639 -7.258 109.165 343.377") # Balance approach
                reply = client.SendCommand("waitforeom")

                # PLC code to open Balance Shield
                S71200_PLC.write_memory_bit(100, 0, True)
                time.sleep(5)
                S71200_PLC.write_memory_bit(100, 0, False)
                time.sleep(1)
                Shield_sensor = S71200_PLC.read_input_bit(0, 0)

                if not Shield_sensor:

                    client.SendCommand("placeplate 9") # Balance point
                    reply = client.SendCommand("waitforeom")

                    # client.SendCommand("movej 1 1046.97 -1.398 124.000 179.77 103.064 343.377") # Safe Pos Balance
                    # reply = client.SendCommand("waitforeom")

                    # client.SendCommand("movej 1 1046.97 -2.902 180.537 178.063 103.542 343.377") # Safe Pos Balance
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
