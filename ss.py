# import S71200_PLC
# from balance_tcp import BalanceTCPClient
# import time

# S71200_PLC.write_memory_bit(100, 0, True)
# time.sleep(5)
# S71200_PLC.write_memory_bit(100, 0, False)
# time.sleep(1)

# import requests

# payload = {"qrdata": ""}
# resp = requests.post("http://127.0.0.1:1880/qr-update", json=payload, timeout=1)

# from log import write_log

# l = write_log("AS_Test")

# import csdf_kafka
# import time

# csdf_kafka.experiment_started(1, 1, "A")
# time.sleep(10)
# csdf_kafka.experiment_finished(1, 1, "A")

import error_task

error_task.add_error_task(exp_id=555, cid=1, rid=1)