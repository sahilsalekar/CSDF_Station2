#!/usr/bin/env python3

import telnetlib
import time

class PyClient:

    def __init__(self, host, port, mode=0):
        print("Initializing connection...")
        self.host = host
        self.port = port
        self.mode = mode
        self.connection = None

        self.Connect()
        self.InitTCS()
        print("✅ Robot connection ready.")

    def Connect(self):
        try:
            self.connection = telnetlib.Telnet(self.host, self.port, timeout=5)
            print("🔌 Telnet connection established.")
        except Exception as e:
            raise Exception(f"[ERROR] Could not establish Telnet connection: {e}")

    def InitTCS(self):
        if not self.connection:
            self.Connect()

        # Attempt to set mode
        try:
            if self.mode == 0:
                self.SendCommand("mode 0")
            else:
                self.SendCommand("mode 1")
        except Exception as e:
            print(f"[WARNING] Could not set mode: {e}. Retrying in 5 seconds...")
            time.sleep(5)
            try:
                # Try again once
                if self.mode == 0:
                    self.SendCommand("mode 0")
                else:
                    self.SendCommand("mode 1")
            except Exception as e:
                raise Exception(f"[FATAL] Failed to set mode twice: {e}")

        # Attempt to select robot
        try:
            self.SendCommand("selectrobot 1")
        except Exception as e:
            raise Exception(f"[FATAL] Could not select robot: {e}")

    def SendCommand(self, command):
        print(f">> {command}")
        self.connection.write((command.encode("ascii") + b"\n"))

        if self.mode == 1:
            _ = self.connection.read_until(b"\r\n").rstrip().decode("ascii")  # Ignore for now

        response = self.connection.read_until(b"\r\n").rstrip().decode("ascii")

        if response.startswith("-"):
            raise Exception(f"TCS error: {response}")

        print(f"<< {response}")
        return response

    def Close(self):
        if self.connection:
            self.connection.close()
            print("🔒 Connection closed.")
