import snap7
from snap7.util import get_bool, set_bool, get_string
from snap7.type import Area
import time

# Connect to PLC
plc = snap7.client.Client()
plc.connect("192.168.1.1", 0, 1)  # Replace with your PLC's IP, rack, and slot

# Function to write to a memory bit (%M)
def write_memory_bit(byte_index, bit_index, value):
    data = plc.read_area(Area.MK, 0, byte_index, 1)
    set_bool(data, 0, bit_index, value)  # Modify Bit
    plc.write_area(Area.MK, 0, byte_index, data)
    print(f"Set %M{byte_index}.{bit_index} to {value}")

# Function to read an input bit (%I)
def read_input_bit(byte_index, bit_index):
    data = plc.read_area(Area.PE, 0, byte_index, 1)
    value = get_bool(data, 0, bit_index)
    print(f"Read %I{byte_index}.{bit_index} -> {value}")
    return value

def read_db_string(db_number, start, size):
    data = plc.db_read(db_number, start, size)
    return get_string(data, 0)  # Skip the first 2 bytes (length info)

def close_connection():
    """Close the PLC connection"""
    plc.disconnect()
    plc.destroy()







