import requests
import os
from dotenv import load_dotenv

load_dotenv()

ASANA_ACCESS_TOKEN = os.getenv("ASANA_ACCESS_TOKEN")
ASANA_PROJECT_ID = os.getenv("ASANA_PROJECT_ID")

url = "https://app.asana.com/api/1.0/tasks"

headers = {
    "Authorization": f"Bearer {ASANA_ACCESS_TOKEN}"
}

data = {
    "data": {
        "name": "Hello World",
        "projects": [ASANA_PROJECT_ID]
    }
}
response = requests.post(url, headers=headers, json=data)

if response.status_code == 201:
    print("Task created successfully.")
else:
    print(f"Error: {response.status_code}")
    print(response.text)