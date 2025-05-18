# robot_setup.py

import time
import pa_pyclient

ROBOT_HOST = "192.168.1.35"  # Replace with the robot's actual IP
ROBOT_PORT = "10100"         # Replace with the robot's actual port

def setup_robot():
    print("Running robot setup...")

    client = pa_pyclient.PyClient(ROBOT_HOST, ROBOT_PORT)

    try:
        # Enable high power if necessary
        is_hp = client.SendCommand("hp")
        if is_hp == "0 0":
            client.SendCommand("hp 1")
            time.sleep(10)

        # Attach the robot to this thread
        client.SendCommand("attach 1")

        # Home if necessary
        is_homed = client.SendCommand("pd 2800")
        if is_homed == "0 0":
            client.SendCommand("home")
        
        # Moving to Home Position

        client.SendCommand("movej 1 1017.83 -2.902 180.537 178.063 103.542 -934.686")
        reply = client.SendCommand("waitforeom")

        if(reply == "0"):
             
             print("HomeComplete")
        
        else:
            
            print("NOTHomed")

            raise RuntimeError("Robot NOT Homed")

        # Send predefined setup commands to the robot
        client.SendCommand("tool 0 0 160 0 0 0")
        time.sleep(0.5)
        client.SendCommand("gripclosepos 110.223")
        time.sleep(0.5)
        client.SendCommand("gripopenpos 115")
        time.sleep(0.5)

        # Station 1
        client.SendCommand("rail 1 -935.664")
        time.sleep(0.5)
        client.SendCommand("stationtype 1 1 1 150 5 0")
        time.sleep(0.5)
        client.SendCommand("palletorigin 1 -892.968 589.776 172.411 89.663 90 180 1 ")
        time.sleep(0.5)
        client.SendCommand("palletx 1 2 -772.74 590.165 172.411")
        time.sleep(0.5)
        client.SendCommand("pallety 1 4 -893.45 319.839 172.411")
        time.sleep(0.5)

        # Station 2
        client.SendCommand("rail 2 -8.903")
        time.sleep(0.5)
        client.SendCommand("stationtype 2 1 1 150 5 0")
        time.sleep(0.5)
        client.SendCommand("palletorigin 2 66.082 596.507 178.247 89.725 90 180 1 ")
        time.sleep(0.5)
        client.SendCommand("palletx 2 2 186.901 595.591 178.247")
        time.sleep(0.5)
        client.SendCommand("pallety 2 4 62.572 325.662 178.247")
        time.sleep(0.5)

         # Station 3
        client.SendCommand("rail 3 905.986")
        time.sleep(0.5)
        client.SendCommand("stationtype 3 1 1 150 5 0")
        time.sleep(0.5)
        client.SendCommand("palletorigin 3 1006.378 583.147 174.371 88.251 90 180 1 ")
        time.sleep(0.5)
        client.SendCommand("palletx 3 2 1128.294 584.229 174.371")
        time.sleep(0.5)
        client.SendCommand("pallety 3 4 1008.841 314.213 174.371")
        time.sleep(0.5)

        # Station 4
        client.SendCommand("rail 4 -948.090")
        time.sleep(0.5)
        client.SendCommand("stationtype 4 1 1 150 5 0")
        time.sleep(0.5)
        client.SendCommand("palletorigin 4 -888.25 584.674 841.587 91.262 90 -180 1 ")
        time.sleep(0.5)
        client.SendCommand("palletx 4 2 -768.353 584.815 841.587")
        time.sleep(0.5)
        client.SendCommand("pallety 4 4 -889.187 315.351 841.587")
        time.sleep(0.5)

        # Station 5
        client.SendCommand("rail 5 -8.886")
        time.sleep(0.5)
        client.SendCommand("stationtype 5 1 1 150 5 0")
        time.sleep(0.5)
        client.SendCommand("palletorigin 5 63.045 587.438 844.044 93.253 90 -180 1 ")
        time.sleep(0.5)
        client.SendCommand("palletx 5 2 182.671 588.389 844.044")
        time.sleep(0.5)
        client.SendCommand("pallety 5 4 62.802 318.069 844.044")
        time.sleep(0.5)

        # Station 6
        client.SendCommand("rail 6 935.165")
        time.sleep(0.5)
        client.SendCommand("stationtype 6 1 1 150 5 0")
        time.sleep(0.5)
        client.SendCommand("palletorigin 6 1009.203 587.387 846.66 91.997 90 -180 1 ")
        time.sleep(0.5)
        client.SendCommand("palletx 6 2 1128.506 587.665 846.66")
        time.sleep(0.5)
        client.SendCommand("pallety 6 4 1006.367 318.266 846.6")
        time.sleep(0.5)

        # Station 7
        client.SendCommand("rail 7 999.837")
        time.sleep(0.5)
        client.SendCommand("stationtype 7 1 1 150 5 0")
        time.sleep(0.5)
        client.SendCommand("palletorigin 7 1337.847 -423.88 750.716 -90.295 90 -180 2 ")
        time.sleep(0.5)
        client.SendCommand("palletx 7 2 1337.874 -457.906 750.716")
        time.sleep(0.5)
        client.SendCommand("pallety 7 4 1247.246 -423.947 750.716")
        time.sleep(0.5)

       

        return client
    
    except Exception as e:
        print(f"Error during robot setup: {e}")
        #                              
        #client.Close()
        raise



    
