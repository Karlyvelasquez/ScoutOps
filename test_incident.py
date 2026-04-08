import json
import urllib.request
from pprint import pprint

try:
    url = "http://127.0.0.1:8000/incident/inc_ea18cb8b2a45"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
        
    print("--- RESPONSE FROM FASTAPI ---")
    pprint(data)
    print("\n--- RESULT EXISTS? ---", "result" in data and data["result"] is not None)
    
except Exception as e:
    print("ERROR:", e)
