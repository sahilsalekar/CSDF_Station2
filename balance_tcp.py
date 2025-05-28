import socket
import time

class BalanceTCPClient:
    def __init__(self, ip='192.168.1.7', port=23, timeout=5):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.sock = None
        self.connect()

    def connect(self):
        """Establish connection to the balance."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.ip, self.port))
            print(f"Connected to balance at {self.ip}:{self.port}")
        except socket.error as e:
            raise
            self.sock = None

    def disconnect(self):
        """Close the socket connection."""
        if self.sock:
            self.sock.close()
            self.sock = None
            print("Disconnected from balance")

    def send_command(self, command: str):
        """Send a raw command to the balance."""
        if not self.sock:
            print("Not connected. Attempting to reconnect...")
            self.connect()

        if self.sock:
            try:
                self.sock.sendall((command + '\r\n').encode())
            except socket.error as e:
                print(f"Send failed: {e}")
                self.disconnect()

    def read_response(self, buffer_size=1024) -> str:
        """Read the response from the balance."""
        if not self.sock:
            print("Not connected. Cannot read.")
            return ""

        try:
            data = self.sock.recv(buffer_size)
            return data.decode().strip()
        except socket.timeout:
            print("Read timed out.")
        except socket.error as e:
            print(f"Read failed: {e}")
            self.disconnect()
        return ""

    def send_and_receive(self, command: str) -> str:
        """Send a command and get the response."""
        self.send_command(command)
        time.sleep(0.1)
        return self.read_response()

    def read_weight(self) -> float:
        """Send 'S' command to read weight and return value in mg (as float)."""
        response = self.send_and_receive("S")
        print(f"Raw response: {response}")

        try:
            # Extract number from format like "SS     14.256 g"
            parts = response.split()
            if len(parts) >= 2:
                weight_g = float(parts[1])
                weight_mg = weight_g * 1000
                print(f"Weight in mg: {weight_mg}")
                return weight_mg
            else:
                print("Unexpected response format.")
        except Exception as e:
            print(f"Failed to parse weight: {e}")

        return 0.0

    def zero_balance(self) -> str:
        """Send 'Z' command to zero the balance."""
        response = self.send_and_receive("Z")
        print(f"Zeroing response: {response}")
        return response

    def __del__(self):
        self.disconnect()
