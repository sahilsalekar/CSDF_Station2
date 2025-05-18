# Vial_to_ventionplace.py

import time

def Vial_to_ventionplace(client):
    """
    Executes Vial_to_ventionplace commands.
    """
    print("Executing Vial_to_ventionplace")
    try:

        # Robot to vention Pos
        client.SendCommand("moveoneaxis 6 -951.417 1")
        reply = client.SendCommand("waitforeom")
        if reply == "0":
            print("Robot moved to vention_pos.")
            client.SendCommand("movej 1 934.068 -75.402 315.594 28.535 109.165 -951.417")
            reply = client.SendCommand("waitforeom")
        
            client.SendCommand("movec 1 -1022.533 -702.976 760.924 -91.275 90 -180 2")
            reply = client.SendCommand("waitforeom")
        

            client.SendCommand("graspplate 117 60 10")
            reply = client.SendCommand("waitforeom")

            client.SendCommand("movec 1 -1022.546 -702.976 934.042 -91.272 90 -180 2")
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

        