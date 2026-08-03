# Vial_to_ventionplace.py

import time

def Vial_to_ventionplace(client):
    """
    Executes Vial_to_ventionplace commands.
    """
    print("Executing Vial_to_ventionplace")
    try:

        # Robot to vention Pos
        client.SendCommand("moveoneaxis 6 -743.301 3")
        reply = client.SendCommand("waitforeom")
        if reply == "0":
            print("Robot moved to vention_pos.")
            client.SendCommand("movej 1 916.34 -56.527 304.236 21.408 109.165 -743.289") # (J5 109.165)
            reply = client.SendCommand("waitforeom")
        
            client.SendCommand("movec 1 -688.82 -679.296 770.656 -90.883 90 -180 2")
            reply = client.SendCommand("waitforeom")
        

            client.SendCommand("graspplate 117 60 10")
            reply = client.SendCommand("waitforeom")

            client.SendCommand("movec 3 -688.809 -679.294 916.34 -90.883 90 -180 2")
            reply = client.SendCommand("waitforeom")

            # Home Pos
            client.SendCommand("movej 3 1017.83 -2.902 180.537 178.063 103.542 -934.686")
            reply = client.SendCommand("waitforeom")

            print("Sucessfully completed vention vial place")

        else:
            print("Robot did not move to vention_pos.")
            raise RuntimeError("Error in Vial_to_ventionplace")

    except Exception as e:
        print(f"Error in Vial_to_ventionplace: {e}")

        