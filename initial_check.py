# initial_check.py

from balance import balance_check
from qr import qr_check

def initial_check(client):

    try:

        # balance check
        balance_check.balance_check(client)

        # qr check
        qr_check.qr_check(client)

    except Exception as e:

        print(f"Error in initial check: {e}")

