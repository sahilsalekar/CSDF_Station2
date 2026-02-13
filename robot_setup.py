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
        
        # Setting Profile speed 2

        client.SendCommand("profile 2 30 0 100 100 0.1 0.1 10 0")
        time.sleep(0.5)
        
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
        client.SendCommand("palletorigin 1 -893.033 592.975 172.411 90.333 90 -180 1 ")
        time.sleep(0.5)
        client.SendCommand("palletx 1 2 -772.332 592.811 172.411")
        time.sleep(0.5)
        client.SendCommand("pallety 1 4 -892.728 321.908 172.411")
        time.sleep(0.5)

        # Station 2
        client.SendCommand("rail 2 -8.903")
        time.sleep(0.5)
        client.SendCommand("stationtype 2 1 1 150 5 0")
        time.sleep(0.5)
        client.SendCommand("palletorigin 2 64.353 592.494 173.352 90.688 90 -180 1 ")
        time.sleep(0.5)
        client.SendCommand("palletx 2 2 184.817 592.337 173.352")
        time.sleep(0.5)
        client.SendCommand("pallety 2 4 62.749 323.349 173.352")
        time.sleep(0.5)

         # Station 3
        client.SendCommand("rail 3 905.986")
        time.sleep(0.5)
        client.SendCommand("stationtype 3 1 1 150 5 0")
        time.sleep(0.5)
        client.SendCommand("palletorigin 3 1008.034 583.95 175.372 90.795 90 -180 1 ")
        time.sleep(0.5)
        client.SendCommand("palletx 3 2 1129.201 584.012 175.372")
        time.sleep(0.5)
        client.SendCommand("pallety 3 4 1008.859 314.509 175.372")
        time.sleep(0.5)

        # Station 4
        client.SendCommand("rail 4 -948.090")
        time.sleep(0.5)
        client.SendCommand("stationtype 4 1 1 150 5 0")
        time.sleep(0.5)
        client.SendCommand("palletorigin 4 -889.645 590.431 838.157 90.028 90 -180 1 ")
        time.sleep(0.5)
        client.SendCommand("palletx 4 2 -769.223 589.615 838.157")
        time.sleep(0.5)
        client.SendCommand("pallety 4 4 -890.725 321.376 838.157")
        time.sleep(0.5)

        # Station 5
        client.SendCommand("rail 5 -8.886")
        time.sleep(0.5)
        client.SendCommand("stationtype 5 1 1 150 5 0")
        time.sleep(0.5)
        client.SendCommand("palletorigin 5 61.232 589.999 843.365 89.777 90 180 1 ")
        time.sleep(0.5)
        client.SendCommand("palletx 5 2 182.308 591.466 843.365")
        time.sleep(0.5)
        client.SendCommand("pallety 5 4 60.863 320.831 843.365")
        time.sleep(0.5)

        # Station 6
        client.SendCommand("rail 6 935.165")
        time.sleep(0.5)
        client.SendCommand("stationtype 6 1 1 150 5 0")
        time.sleep(0.5)
        client.SendCommand("palletorigin 6 1007.598 590.609 847.583 88.636 90 180 1 ")
        time.sleep(0.5)
        client.SendCommand("palletx 6 2 1128.859 589.333 847.583")
        time.sleep(0.5)
        client.SendCommand("pallety 6 4 1004.118 319.997 847.583")
        time.sleep(0.5)

        # Station 7
        client.SendCommand("rail 7 840.054")
        time.sleep(0.5)
        client.SendCommand("stationtype 7 1 1 150 5 0")
        time.sleep(0.5)
        client.SendCommand("palletorigin 7 1031.583 -512.556 421.953 0.845 90 180 2 ")
        time.sleep(0.5)
        client.SendCommand("palletx 7 2 1029.697 -570.541 421.953")
        time.sleep(0.5)
        client.SendCommand("pallety 7 4 918.805 -508.94 421.953")
        time.sleep(0.5)

        # Station 8 qr
        client.SendCommand("rail 8 999.837")
        time.sleep(0.5)
        client.SendCommand("stationtype 8 1 1 150 5 0")
        time.sleep(0.5)
        client.SendCommand("palletorigin 8 1541.68 69.65 484.915 88.446 90 180 2 ")
        # time.sleep(0.5)
        # client.SendCommand("palletx 8 2 1277.898 -464.614 749.614")
        # time.sleep(0.5)
        # client.SendCommand("pallety 8 4 1187.184 -432.869 749.614")
        # time.sleep(0.5)

        # Station 9 balance
        client.SendCommand("rail 9 343.377")
        time.sleep(0.5)
        client.SendCommand("stationtype 9 1 1 200 5 0")
        time.sleep(0.5)
        client.SendCommand("palletorigin 9 596.39 362.908 849.639 88.64 90 180 1 ")
        # time.sleep(0.5)
        # client.SendCommand("palletx 9 2 1277.898 -464.614 749.614")
        # time.sleep(0.5)
        # client.SendCommand("pallety 9 4 1187.184 -432.869 749.614")
        # time.sleep(0.5)

       

        return client
    
    except Exception as e:
        print(f"Error during robot setup: {e}")
        #                              
        #client.Close()
        raise
