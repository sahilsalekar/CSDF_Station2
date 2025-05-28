import time

def failvial(client):

    print("Executing fialvial")
    try:

        #Move robot to fail vial
        client.SendCommand("moveoneaxis 6 431.523 1")
        reply = client.SendCommand("waitforeom")
        if reply == "0":
            print("Robot moved to fail vial.")

            client.SendCommand("moveoneaxis 1 182.018 1")
            reply = client.SendCommand("waitforeom")

            client.SendCommand("movec 1 982.532 -237.697 182.081 -89.215 90 180 2")
            reply = client.SendCommand("waitforeom")
        
            client.SendCommand("graspplate 117 60 10")
            reply = client.SendCommand("waitforeom")

            time.sleep(1)

            client.SendCommand("movej 1 182.018 -2.902 180.537 178.063 103.542 431.523")
            reply = client.SendCommand("waitforeom")

        else:
            print("Did not move to fail vial")
            raise RuntimeError("Failed to move to fial vial! Stopping Execution.")


    except Exception as e:
        print(f"Error in fail vial: {e}")
        raise