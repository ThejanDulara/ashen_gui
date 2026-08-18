import requests
import json

api_key = "6e1a6346-bb07-4b3f-8653-0c5dab195512"
# 1. get token
res = requests.post("https://api.liveavatar.com/v1/sessions/token", 
    headers={"x-api-key": api_key, "Content-Type": "application/json"}, 
    json={"mode": "FULL", "avatar_id": "073b60a9-89a8-45aa-8902-c358f64d2852", "avatar_persona": {}}
)
token = res.json()["data"]["session_token"]
print("Token:", token)

# 2. start session
res2 = requests.post("https://api.liveavatar.com/v1/sessions/start",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json={}
)
print("Start res:", res2.status_code)
print(json.dumps(res2.json(), indent=2))
