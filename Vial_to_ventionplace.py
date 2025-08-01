# Vial_to_ventionplace.py

import time

def Vial_to_ventionplace(client):
    """
    Executes Vial_to_ventionplace commands.
    """
    print("Executing Vial_to_ventionplace")
    try:

        # Robot to vention Pos
        client.SendCommand("moveoneaxis 6 -743.301 1")
        reply = client.SendCommand("waitforeom")
        if reply == "0":
            print("Robot moved to vention_pos.")
            client.SendCommand("movej 1 887.921 -57.195 305.335 21.405 109.165 -743.301") # (J5 109.165)
            reply = client.SendCommand("waitforeom")
        
            client.SendCommand("movec 1 -688.556 -682.052 761.624 -90.455 90 -180 2")
            reply = client.SendCommand("waitforeom")
        

            client.SendCommand("graspplate 117 60 10")
            reply = client.SendCommand("waitforeom")

            client.SendCommand("movec 1 -688.571 -682.051 887.92 -90.454 90 -180 2")
            reply = client.SendCommand("waitforeom")

            # Home Pos
            client.SendCommand("movej 1 1017.83 -2.902 180.537 178.063 103.542 -934.686")
            reply = client.SendCommand("waitforeom")

            print("Sucessfully completed vention vial place")

        else:
            print("Robot did not move to vention_pos.")
            raise RuntimeError("Error in Vial_to_ventionplace")

    except Exception as e:
        print(f"Error in Vial_to_ventionplace: {e}")

        