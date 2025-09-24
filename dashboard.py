import requests
from datetime import datetime

class Dashboard:
    def __init__(self, base_url='http://130.159.92.210/api'):
        self.base_url = base_url

    def get_free_reactor(self):
        try:
            response = requests.get(f'{self.base_url}/get_free_reactor')
            response.raise_for_status() # checks for HTTP response
            data = response.json()
            return data 
        except requests.RequestException as e:
            print(f"[ERROR] Failed to get free reactor: {e}")
            return None

    def check_for_experiments(self):
        try:
            response = requests.get(f'{self.base_url}/check_for_experiments?include_dosed=true&include_undosed=false')
            response.raise_for_status()
            data = response.json()
            return data
        except requests.RequestException as e:
            print(f"[ERROR] Failed to get new experiment: {e}")
            return None
        
    def check_for_ready_experiments(self):
        try:
            response = requests.get(f'{self.base_url}/get_ready_experiment')
            response.raise_for_status()
            data = response.json()
            return data
        except requests.RequestException as e:
            print(f"[ERROR] Failed to get new experiment: {e}")
            return None
        
    def get_experiment_id(self, vial_id):
        try:
            response = requests.get(f'{self.base_url}/get_exp_for_vial?vial_id={vial_id}')
            response.raise_for_status()
            data = response.json()
            return data
        except requests.RequestException as e:
            print(f"[ERROR] Failed to get experiment id: {e}")
            return None

    def check_exp_status(self, exp_id):
        try:
            response = requests.get(f'{self.base_url}/check_exp_status?exp_id={exp_id}')
            response.raise_for_status()
            data = response.json()
            return data
        except requests.RequestException as e:
            print(f"[ERROR] Failed to get experiment status: {e}")
            return None
        
    def get_crystallines_online(self):
        try:
            response = requests.get(f'{self.base_url}/get_crystallines_online')
            response.raise_for_status()
            data = response.json()
            return data
        except requests.RequestException as e:
            print(f"[ERROR] Failed to get crystallines online: {e}")
            return None

    def mark_reactor_free(self, cid, rid):
        try:
            response = requests.post(f'{self.base_url}/mark_reactor_free?cid={cid}&rid={rid}')
            response.raise_for_status()
            data = response.json()
            return data
        except requests.RequestException as e:
            print(f"[ERROR] Failed to mark reactor free: {e}")
            return None

    def initiate_experiment(self, exp_id, cid, rid):
        try:
            response = requests.post(f'{self.base_url}/initiate_experiment?exp_id={exp_id}&cid={cid}&rid={rid}')
            response.raise_for_status()
            data = response.json()
            return data
        except requests.RequestException as e:
            print(f"[ERROR] Failed to initiate experiment: {e}")
            return None
        
    def add_vial_mass(self, named_time, mass, exp_id):
        try:
            time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            payload = {
                "time": time_now,
                "named_time": named_time,
                "mass": mass,
                "exp_id": exp_id
            }
            response = requests.post(f'{self.base_url}/add_vial_mass', json=payload)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.RequestException as e:
            print(f"[ERROR] Failed to add vial mass: {e}")
            return None




    
    

