import time

def failvial(client):

    print("Executing fialvial")
    try:

        #Move robot to fail vial
        client.SendCommand("moveoneaxis 6 431.523 1")
        reply = client.SendCommand("waitforeom")
        if reply == "0":
            print("Robot moved to fail vial.")

            client.SendCommand("moveoneaxis 4 -56.775 1")
            reply = client.SendCommand("waitforeom")

            client.SendCommand("moveoneaxis 1 146.638 1")
            reply = client.SendCommand("waitforeom")
        
            client.SendCommand("graspplate 117 60 10")
            reply = client.SendCommand("waitforeom")

            time.sleep(1)

        else:
            print("Did not move to fail vial")
            raise RuntimeError("Failed to move to fial vial! Stopping Execution.")


    except Exception as e:
        print(f"Error in fail vial: {e}")
        raise