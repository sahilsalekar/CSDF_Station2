# import S71200_PLC
# from balance_tcp import BalanceTCPClient
# import time

# S71200_PLC.write_memory_bit(100, 0, True)
# time.sleep(5)
# S71200_PLC.write_memory_bit(100, 0, False)
# time.sleep(1)

import requests

payload = {"qrdata": ""}
resp = requests.post("http://127.0.0.1:1880/qr-update", json=payload, timeout=1)