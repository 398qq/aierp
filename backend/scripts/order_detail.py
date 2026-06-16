import json, urllib.request

data = json.dumps({"username":"admin","password":"admin123"}).encode()
req = urllib.request.Request("http://localhost:8080/api/v1/auth/login", data=data, headers={"Content-Type":"application/json"})
token = json.loads(urllib.request.urlopen(req).read())["data"]["token"]

# Get one order in full
req = urllib.request.Request("http://localhost:8080/api/v1/sales-orders/74", headers={"Authorization": f"Bearer {token}"})
order = json.loads(urllib.request.urlopen(req).read())["data"]
print(json.dumps(order, ensure_ascii=False, indent=2))
