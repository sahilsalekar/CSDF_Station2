import requests

class nodered:
    def __init__(self, node_red_url):
        self.node_red_url = node_red_url

    def distask(self, robot_id, task_type, position):
        # Format: "1 1 A"
        payload = f"{robot_id} {task_type} {position}"
        try:
            response = requests.post(self.node_red_url, json={"task": payload})
            
        except Exception as e:
            raise

    def disQRdata(self, QR_Data):
        payload =f"{QR_Data}"
        try:
            response = requests.post(self.node_red_url, json={"QR_data": payload})

        except Exception as e:
            raise
