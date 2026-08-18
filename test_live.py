import requests
import json

res = requests.post("https://api.liveavatar.com/v1/sessions/token", 
    headers={"x-api-key": "6e1a6346-bb07-4b3f-8653-0c5dab195512", "Content-Type": "application/json"}, 
    json={
        "mode": "FULL",
        "avatar_id": "073b60a9-89a8-45aa-8902-c358f64d2852",
        "avatar_persona": {} 
    }
)
print("status:", res.status_code)
print(json.dumps(res.json(), indent=2))
