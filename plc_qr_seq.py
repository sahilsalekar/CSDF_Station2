import time
import S71200_PLC

def plc_qr_seq():
    print("Executing PLC QR Sequence")

    try:
        # Trigger clr bit
        S71200_PLC.write_memory_bit(10, 1, True)
        time.sleep(1)
        S71200_PLC.write_memory_bit(10, 1, False)
        time.sleep(1)

        # Trigger sequence
        S71200_PLC.write_memory_bit(10, 0, True)
        time.sleep(1)
        S71200_PLC.write_memory_bit(10, 0, False)
        time.sleep(11)  # wait for scan

        # Read bits
        QR_Comp = S71200_PLC.read_input_bit(4, 0)
        QR_Error = S71200_PLC.read_input_bit(5, 0)

        # Process result
        if QR_Comp and not QR_Error:
            QR_Data = S71200_PLC.read_db_string(1, 136, 20)
            print(f"QR Scan Successful! : {QR_Data}")

            S71200_PLC.write_memory_bit(10, 1, True)
            time.sleep(1)
            S71200_PLC.write_memory_bit(10, 1, False)

            return {"success": True, "data": QR_Data}

        elif QR_Comp and QR_Error:
            QR_Data = S71200_PLC.read_db_string(1, 136, 20)
            print(f"QR Scan Unsuccessful! : {QR_Data}")

            S71200_PLC.write_memory_bit(10, 1, True)
            time.sleep(1)
            S71200_PLC.write_memory_bit(10, 1, False)

            return {"success": False, "data": QR_Data}

        else:
            print("No valid QR result received.")
            return {"success": False, "data": None}

    except Exception as e:
        print(f"[ERROR] Exception in plc_qr_seq: {e}")
        return {"success": False, "data": None, "error": str(e)}
