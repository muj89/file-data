import json

data = {
    "message": "Hello from Python!",
    "status": "success",
    "items": [1, 2, 3]
}

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("data.json created.")
