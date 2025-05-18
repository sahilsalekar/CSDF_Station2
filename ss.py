import requests

data = {
    1, 1, "A"
}

res = requests.post("http://localhost:1880/task-update", json=data)
print(res.status_code, res.text)
