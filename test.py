import requests

url = "http://127.0.0.1:8000/ask"
payload = {
    "question": "What was the net profit in Q4 2022?"
}

response = requests.post(url, json=payload)

print("Answer:", response.json())
