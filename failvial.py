import time
import requests
import Vial_to_ventionplace

SEND_VIAL_API  = "http://localhost:8005/send_vial" 

def failvial(client):

    print("Executing fialvial")
    try:

        # Check for send vial to staion 3
        while True:
            try:
                response = requests.get(SEND_VIAL_API, timeout=10)
                response.raise_for_status()

                resp = response.json()

                if resp.get("sendvial") is True:
                    print("Sending vial to Station 3")
                    break

                print("Holding for Station 3 (Failvial)")

            except (requests.RequestException, ValueError) as e:
                print(f"Station 3 API error: {e}")

            time.sleep(10)

        print("Continuing to vial to ventionplace")

        Vial_to_ventionplace.Vial_to_ventionplace(client)

        print("Successfuly completed vial to vention place")

        print("Fail vial station 2 success")

        # client.SendCommand("moveoneaxis 6 431.523 1")
        # reply = client.SendCommand("waitforeom")
        # if reply == "0":
        #     print("Robot moved to fail vial.")

        #     client.SendCommand("moveoneaxis 1 182.018 1")
        #     reply = client.SendCommand("waitforeom")

        #     client.SendCommand("movec 1 964.349 -316.649 182.085 -89.027 90 180 2")
        #     reply = client.SendCommand("waitforeom")
        
        #     client.SendCommand("graspplate 117 60 10")
        #     reply = client.SendCommand("waitforeom")

        #     time.sleep(1)

        #     client.SendCommand("movej 1 182.018 -2.902 180.537 178.063 103.542 431.523")
        #     reply = client.SendCommand("waitforeom")

        # else:
        #     print("Did not move to fail vial")
        #     raise RuntimeError("Failed to move to fial vial! Stopping Execution.")


    except Exception as e:
        print(f"Error in fail vial: {e}")
        raise